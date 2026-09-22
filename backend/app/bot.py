import asyncio
import logging
from datetime import datetime
from html import escape
from aiogram import Bot,Dispatcher,Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message,InlineKeyboardMarkup,InlineKeyboardButton,WebAppInfo
from sqlalchemy import select, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings
from .db import engine
from .models import AppSetting,BotMenuItem,CustomField,Promotion,Advertisement,Plan,Broadcast,User,Subscription,AbuseViolation,NodeAgent

logger = logging.getLogger("remnawave.broadcast")

router=Router()

_BOT_TEXT = {
    "ru": {
        "welcome": "Добро пожаловать в {name}!",
        "prices": "Актуальные цены",
        "scope": " для выбранных тарифов",
        "open": "🛒 Открыть магазин",
        "promo_usage": "Использование: /promo КОД",
        "promo_ready": "Промокод <b>{code}</b>. Откройте магазин и примените его к тарифу.",
        "gift_ready": "Подарок <b>{code}</b>. Откройте магазин, чтобы активировать его.",
        "ops_denied": "Команда только для владельца магазина.",
        "ops_status": "Открытых нарушений: {violations}. Агентов за 5 минут: {agents}. Панель: {url}",
    },
    "en": {
        "welcome": "Welcome to {name}!",
        "prices": "Current prices",
        "scope": " for selected plans",
        "open": "🛒 Open shop",
        "promo_usage": "Usage: /promo CODE",
        "promo_ready": "Promo code <b>{code}</b>. Open the shop and apply it to a plan.",
        "gift_ready": "Gift <b>{code}</b>. Open the shop to activate it.",
        "ops_denied": "This command is only for the shop owner.",
        "ops_status": "Open violations: {violations}. Agents seen in 5 minutes: {agents}. Panel: {url}",
    },
}

def _lang(message: Message | None = None) -> str:
    code = ""
    if message is not None and message.from_user and message.from_user.language_code:
        code = message.from_user.language_code
    code = (code or settings.default_language or "ru").lower()
    return "en" if code.startswith("en") else "ru"

def _tr(lang: str, key: str, **kwargs) -> str:
    table = _BOT_TEXT.get(lang) or _BOT_TEXT["ru"]
    text = table[key]
    for name, value in kwargs.items():
        text = text.replace("{" + name + "}", str(value))
    return text

async def get_bot_config():
    async with AsyncSession(engine,expire_on_commit=False) as db:
        vals={x.key:x.value for x in (await db.execute(select(AppSetting))).scalars().all()}
        menu=(await db.execute(select(BotMenuItem).where(BotMenuItem.enabled.is_(True)).order_by(BotMenuItem.sort_order,BotMenuItem.id))).scalars().all()
        fields=(await db.execute(select(CustomField).where(CustomField.enabled.is_(True)).order_by(CustomField.sort_order,CustomField.id))).scalars().all()
        now=datetime.utcnow()
        ads=(await db.execute(select(Advertisement).where(Advertisement.enabled.is_(True)).order_by(Advertisement.sort_order,Advertisement.id))).scalars().all()
        ads=[a for a in ads if (not a.starts_at or now>=a.starts_at) and (not a.ends_at or now<=a.ends_at)]
        promos=(await db.execute(select(Promotion).where(Promotion.enabled.is_(True)).order_by(Promotion.id.desc()))).scalars().all()
        promos=[p for p in promos if (not p.starts_at or now>=p.starts_at) and (not p.ends_at or now<=p.ends_at)]
        plans=(await db.execute(select(Plan).where(Plan.enabled.is_(True)).order_by(Plan.id))).scalars().all()
        return vals,menu,fields,ads,promos,plans

def promo_text(promos,plans,lang="ru"):
    chunks=[]
    discount_word = "скидка" if lang != "en" else "off"
    for p in promos:
        scope="" if not p.plan_ids else _tr(lang, "scope")
        chunks.append(f"🎁 <b>{escape(p.name)}</b> — {discount_word} {p.value:g}{'%' if p.kind=='percent' else ' ₽'}{scope}.\n{escape(p.description)}".strip())
    return "\n\n".join(chunks)


def broadcast_recipient_query(target: str, now: datetime):
    """Users with a Telegram id. Active joins subscriptions, so the query is distinct."""
    stmt = select(User.id, User.telegram_id).where(User.telegram_id.is_not(None))
    if target == "active":
        stmt = stmt.join(Subscription, Subscription.user_id == User.id).where(Subscription.expires_at > now)
    elif target == "inactive":
        active_ids = select(Subscription.user_id).where(Subscription.expires_at > now)
        stmt = stmt.where(~User.id.in_(active_ids))
    return stmt.distinct().order_by(User.id)


async def _telegram_post(client, method: str, payload: dict):
    url = f"https://api.telegram.org/bot{settings.bot_token}/{method}"
    response = None
    for attempt in range(2):
        response = await client.post(url, json=payload)
        if response.status_code != 429 or attempt == 1:
            return response
        wait = 1.0
        try:
            wait = float(response.json().get("parameters", {}).get("retry_after", 1))
        except Exception:
            wait = 1.0
        await asyncio.sleep(min(max(wait, 0.5), 30))
    return response


async def _mark_broadcast_failed(broadcast_id: int) -> None:
    async with AsyncSession(engine, expire_on_commit=False) as db:
        row = await db.get(Broadcast, broadcast_id)
        if row and row.status == "sending":
            row.status = "failed"
            row.finished_at = datetime.utcnow()
            await db.commit()


async def broadcast_worker(bot: Bot):
    import httpx
    while True:
        claimed = None
        try:
            async with AsyncSession(engine, expire_on_commit=False) as db:
                row = (await db.execute(sql_text("UPDATE broadcasts SET status='sending' WHERE id=(SELECT id FROM broadcasts WHERE status='queued' ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING id"))).first()
                await db.commit()
                if not row:
                    await asyncio.sleep(2)
                    continue
                claimed = int(row[0])
                item = await db.get(Broadcast, claimed)
                if not item:
                    claimed = None
                    continue
                now = datetime.utcnow()
                recipients = (await db.execute(broadcast_recipient_query(item.target, now))).all()
                sent = int(item.sent_count or 0)
                failed = int(item.failed_count or 0)
                start = sent + failed
                async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
                    for index, recipient in enumerate(recipients):
                        if index < start:
                            continue
                        try:
                            markup = {"inline_keyboard": [[{"text": item.button_text, "url": item.button_url}]]} if item.button_text and item.button_url else None
                            if item.image_url:
                                payload = {"chat_id": recipient.telegram_id, "photo": item.image_url, "caption": item.text, "parse_mode": "HTML"}
                                if markup:
                                    payload["reply_markup"] = markup
                                response = await _telegram_post(client, "sendPhoto", payload)
                            else:
                                payload = {"chat_id": recipient.telegram_id, "text": item.text, "parse_mode": "HTML"}
                                if markup:
                                    payload["reply_markup"] = markup
                                response = await _telegram_post(client, "sendMessage", payload)
                            if response is not None and response.is_success:
                                sent += 1
                            else:
                                failed += 1
                        except Exception:
                            logger.exception("broadcast delivery failed for id %s", claimed)
                            failed += 1
                        item.sent_count = sent
                        item.failed_count = failed
                        await db.commit()
                        await asyncio.sleep(0.04)
                item.status = "completed"
                item.finished_at = datetime.utcnow()
                await db.commit()
                claimed = None
        except Exception:
            logger.exception("broadcast worker failed")
            if claimed is not None:
                try:
                    await _mark_broadcast_failed(claimed)
                except Exception:
                    logger.exception("broadcast failure status was not saved")
            await asyncio.sleep(5)

@router.message(CommandStart())
async def start(message:Message):
    vals,menu,fields,ads,promos,plans=await get_bot_config()
    lang=_lang(message)
    start_arg=""
    parts=(message.text or "").split(maxsplit=1)
    if len(parts)>1:
        start_arg=parts[1].strip().split()[0]
    gift_code=start_arg.upper() if start_arg.upper().startswith("GIFT_") else ""
    buttons=[]; field_text=[]
    for m in menu:
        if m.item_type=="webapp":
            url=m.action or settings.mini_app_url
            if not url.startswith("https://"): continue
            buttons.append([InlineKeyboardButton(text=m.title,web_app=WebAppInfo(url=url))])
        elif m.item_type=="url":
            if not m.action.startswith("https://"): continue
            buttons.append([InlineKeyboardButton(text=m.title,url=m.action)])
        elif m.item_type=="field":
            f=next((x for x in fields if x.key==m.action),None)
            if f: field_text.append(f"<b>{escape(f.label)}</b>\n{escape(f.value)}")
    shop_url=settings.mini_app_url
    if gift_code:
        join="&" if "?" in shop_url else "?"
        shop_url=f"{shop_url}{join}gift={gift_code}"
    if not buttons: buttons=[[InlineKeyboardButton(text=_tr(lang,"open"),web_app=WebAppInfo(url=shop_url))]]
    elif gift_code:
        buttons.append([InlineKeyboardButton(text=_tr(lang,"open"),web_app=WebAppInfo(url=shop_url))])
    name=escape(vals.get("bot_name") or "VPN Shop"); text=_tr(lang,"welcome",name=name)
    pt=promo_text(promos,plans,lang)
    if gift_code: text += "\n\n"+_tr(lang,"gift_ready",code=escape(gift_code))
    if pt: text += "\n\n"+pt
    price_lines=[]
    for plan in plans:
        promo_obj=next((x for x in promos if not x.plan_ids or plan.id in x.plan_ids),None)
        price=float(plan.price)
        if promo_obj:
            discount=price*float(promo_obj.value)/100 if promo_obj.kind=="percent" else min(price,float(promo_obj.value))
            price_lines.append(f"• {escape(plan.name)}: <s>{price:.2f} ₽</s> <b>{price-discount:.2f} ₽</b>")
        else: price_lines.append(f"• {escape(plan.name)}: <b>{price:.2f} ₽</b>")
    if price_lines: text += "\n\n💳 <b>"+_tr(lang,"prices")+"</b>\n"+"\n".join(price_lines)
    for a in ads:
        text += f"\n\n📣 <b>{escape(a.title)}</b>\n{escape(a.text)}"
        if a.button_text and a.button_url: buttons.append([InlineKeyboardButton(text=a.button_text,url=a.button_url)])
    if field_text: text += "\n\n"+"\n\n".join(field_text)
    markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    start_image=vals.get("bot_start_image","")
    if start_image:
        photo_url=start_image if start_image.startswith("https://") else settings.public_base_url.rstrip("/")+"/"+start_image.lstrip("/")
        try:
            await message.answer_photo(photo=photo_url,caption=text,reply_markup=markup,parse_mode="HTML")
            return
        except Exception:
            # Image delivery must never break the bot's core /start response.
            pass
    await message.answer(text,reply_markup=markup,parse_mode="HTML")

@router.message(Command("promo"))
async def promo(message:Message):
    lang=_lang(message)
    code=(message.text or "").split(maxsplit=1)
    if len(code)<2:
        await message.answer(_tr(lang,"promo_usage"))
        return
    # Deep-link into Mini App with the code; server validates it again before payment.
    from urllib.parse import quote
    promo_code=code[1].strip().upper()
    await message.answer(_tr(lang,"promo_ready",code=escape(promo_code)),reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=_tr(lang,"open"),web_app=WebAppInfo(url=settings.mini_app_url+"?promo="+quote(promo_code)))] ]),parse_mode="HTML")

@router.message(Command("ops"))
async def ops(message: Message):
    lang = _lang(message)
    if not message.from_user or int(message.from_user.id) != int(settings.admin_telegram_id or 0):
        await message.answer(_tr(lang, "ops_denied"))
        return
    from datetime import timedelta
    from sqlalchemy import func
    async with AsyncSession(engine, expire_on_commit=False) as db:
        violations = int(await db.scalar(select(func.count()).select_from(AbuseViolation).where(AbuseViolation.status == "open")) or 0)
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        agents = int(await db.scalar(select(func.count()).select_from(NodeAgent).where(NodeAgent.last_seen_at.is_not(None), NodeAgent.last_seen_at >= cutoff)) or 0)
    url = f"https://{settings.admin_domain}" if settings.admin_domain and settings.admin_domain != "localhost" else settings.public_base_url
    buttons = [[InlineKeyboardButton(text="Панель" if lang == "ru" else "Panel", url=url)]]
    await message.answer(_tr(lang, "ops_status", violations=violations, agents=agents, url=escape(url)), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

async def main():
    if not settings.bot_token: raise RuntimeError("BOT_TOKEN is empty")
    bot=Bot(settings.bot_token); dp=Dispatcher(); dp.include_router(router)
    asyncio.create_task(broadcast_worker(bot))
    await dp.start_polling(bot)
if __name__=="__main__": asyncio.run(main())
