import asyncio
from datetime import datetime
from html import escape
from aiogram import Bot,Dispatcher,Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message,InlineKeyboardMarkup,InlineKeyboardButton,WebAppInfo
from sqlalchemy import select, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings
from .db import engine
from .models import AppSetting,BotMenuItem,CustomField,Promotion,Advertisement,Plan,Broadcast,User,Subscription

router=Router()

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

def promo_text(promos,plans):
    chunks=[]
    for p in promos:
        scope="" if not p.plan_ids else " для выбранных тарифов"
        chunks.append(f"🎁 <b>{escape(p.name)}</b> — скидка {p.value:g}{'%' if p.kind=='percent' else ' ₽'}{scope}.\n{escape(p.description)}".strip())
    return "\n\n".join(chunks)


async def broadcast_worker(bot:Bot):
    import httpx
    while True:
        try:
            async with AsyncSession(engine,expire_on_commit=False) as db:
                row=(await db.execute(sql_text("UPDATE broadcasts SET status='sending' WHERE id=(SELECT id FROM broadcasts WHERE status='queued' ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING id"))).first()
                await db.commit()
                if not row:
                    await asyncio.sleep(2); continue
                b=await db.get(Broadcast,int(row[0]))
                if not b: continue
                if b.target=="active":
                    users=(await db.execute(select(User).join(Subscription,Subscription.user_id==User.id).where(User.telegram_id.is_not(None),Subscription.expires_at>datetime.utcnow()))).scalars().all()
                elif b.target=="inactive":
                    users=(await db.execute(select(User).where(User.telegram_id.is_not(None),~User.id.in_(select(Subscription.user_id).where(Subscription.expires_at>datetime.utcnow()))))).scalars().all()
                else:
                    users=(await db.execute(select(User).where(User.telegram_id.is_not(None)))).scalars().all()
                sent=failed=0
                async with httpx.AsyncClient(timeout=15) as client:
                    for u in users:
                        try:
                            markup={"inline_keyboard":[[{"text":b.button_text,"url":b.button_url}]]} if b.button_text and b.button_url else None
                            if b.image_url:
                                payload={"chat_id":u.telegram_id,"photo":b.image_url,"caption":b.text,"parse_mode":"HTML"}
                                if markup: payload["reply_markup"]=markup
                                r=await client.post(f"https://api.telegram.org/bot{settings.bot_token}/sendPhoto",json=payload)
                            else:
                                payload={"chat_id":u.telegram_id,"text":b.text,"parse_mode":"HTML"}
                                if markup: payload["reply_markup"]=markup
                                r=await client.post(f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",json=payload)
                            if r.is_success: sent+=1
                            else: failed+=1
                        except Exception: failed+=1
                        await asyncio.sleep(0.04)
                b.sent_count=sent; b.failed_count=failed; b.status="completed"; b.finished_at=datetime.utcnow(); await db.commit()
        except Exception:
            await asyncio.sleep(5)

@router.message(CommandStart())
async def start(message:Message):
    vals,menu,fields,ads,promos,plans=await get_bot_config()
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
    if not buttons: buttons=[[InlineKeyboardButton(text="🛒 Открыть магазин",web_app=WebAppInfo(url=settings.mini_app_url))]]
    name=escape(vals.get("bot_name") or "VPN Shop"); text=f"Добро пожаловать в {name}!"
    pt=promo_text(promos,plans)
    if pt: text += "\n\n"+pt
    price_lines=[]
    for plan in plans:
        promo_obj=next((x for x in promos if not x.plan_ids or plan.id in x.plan_ids),None)
        price=float(plan.price)
        if promo_obj:
            discount=price*float(promo_obj.value)/100 if promo_obj.kind=="percent" else min(price,float(promo_obj.value))
            price_lines.append(f"• {escape(plan.name)}: <s>{price:.2f} ₽</s> <b>{price-discount:.2f} ₽</b>")
        else: price_lines.append(f"• {escape(plan.name)}: <b>{price:.2f} ₽</b>")
    if price_lines: text += "\n\n💳 <b>Актуальные цены</b>\n"+"\n".join(price_lines)
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
    code=(message.text or "").split(maxsplit=1)
    if len(code)<2:
        await message.answer("Использование: /promo КОД")
        return
    # Deep-link into Mini App with the code; server validates it again before payment.
    from urllib.parse import quote
    await message.answer(f"Промокод <b>{code[1].strip().upper()}</b>. Откройте магазин и примените его к тарифу.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 Открыть магазин",web_app=WebAppInfo(url=settings.mini_app_url+"?promo="+quote(code[1].strip().upper())))] ]),parse_mode="HTML")

async def main():
    if not settings.bot_token: raise RuntimeError("BOT_TOKEN is empty")
    bot=Bot(settings.bot_token); dp=Dispatcher(); dp.include_router(router)
    asyncio.create_task(broadcast_worker(bot))
    await dp.start_polling(bot)
if __name__=="__main__": asyncio.run(main())
