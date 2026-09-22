"""Operator platform: abuse score, node agent, API keys, signed webhooks, SMTP."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .abuse import ANALYZERS, score_observations, source_prefix
from .db import get_db
from .models import (
    AbuseViolation,
    AgentAction,
    ConnectionObservation,
    DeviceBlacklist,
    NodeAgent,
    OutboundWebhook,
    PlatformPlugin,
    ShopApiKey,
    Subscription,
    User,
)
from .security import encrypt_secret, require_permission

router = APIRouter()
DEFAULT_POLICY = {
    "min_score": 50,
    "max_concurrent_ips": 0,
    "cgnat_buffer": 3,
    "max_travel_km": 50,
    "max_accounts_per_hwid": 2,
    "auto_hard_block": False,
    "hard_score": 80,
    "analyzers": {name: True for name in ANALYZERS},
}


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def reject_restricted(user) -> None:
    if getattr(user, "restricted_at", None):
        raise HTTPException(403, "Доступ ограничен")


async def _plugin_on(db: AsyncSession, key: str) -> bool:
    row = (await db.execute(select(PlatformPlugin).where(PlatformPlugin.key == key))).scalar_one_or_none()
    return True if row is None else bool(row.enabled)


async def _require_plugin(db: AsyncSession, key: str) -> None:
    if not await _plugin_on(db, key):
        raise HTTPException(503, "Модуль отключён")


async def _policy(db: AsyncSession) -> dict:
    from .models import AppSetting

    row = await db.get(AppSetting, "abuse_policy")
    if not row or not row.value:
        return json.loads(json.dumps(DEFAULT_POLICY))
    try:
        data = json.loads(row.value)
    except json.JSONDecodeError:
        return json.loads(json.dumps(DEFAULT_POLICY))
    merged = json.loads(json.dumps(DEFAULT_POLICY))
    merged.update({k: v for k, v in data.items() if k != "analyzers"})
    if isinstance(data.get("analyzers"), dict):
        merged["analyzers"].update(data["analyzers"])
    return merged


async def _agent(db: AsyncSession, token: str) -> NodeAgent:
    row = (await db.execute(select(NodeAgent).where(NodeAgent.token_hash == _hash(token)))).scalar_one_or_none()
    if not row or not row.enabled:
        raise HTTPException(401, "Агент не авторизован")
    return row


class PolicyIn(BaseModel):
    min_score: int = Field(ge=1, le=100)
    max_concurrent_ips: int = Field(ge=0, le=100)
    cgnat_buffer: int = Field(ge=0, le=20)
    max_travel_km: int = Field(ge=1, le=20000)
    max_accounts_per_hwid: int = Field(ge=1, le=50)
    auto_hard_block: bool = False
    hard_score: int = Field(ge=1, le=100)
    analyzers: dict[str, bool] = Field(default_factory=dict)


class BlacklistIn(BaseModel):
    hwid: str = Field(min_length=8, max_length=128)
    action: str = Field(pattern="^(alert|block)$")
    note: str = Field(default="", max_length=500)


class ObservationIn(BaseModel):
    ip: str = Field(max_length=64)
    remnawave_uuid: str | None = Field(default=None, max_length=64)
    asn: str | None = Field(default=None, max_length=32)
    asn_org: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=16)
    lat: float | None = None
    lon: float | None = None
    user_agent: str | None = Field(default=None, max_length=255)
    hwid: str | None = Field(default=None, max_length=128)
    mobile: bool = False
    torrent: bool = False


class ObservationBatch(BaseModel):
    items: list[ObservationIn] = Field(max_length=200)


class HeartbeatIn(BaseModel):
    cpu: str = Field(default="", max_length=32)
    mem: str = Field(default="", max_length=32)
    disk: str = Field(default="", max_length=32)
    xray_ok: bool | None = None
    version: str = Field(default="1", max_length=32)


class ApiKeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    scopes: str = Field(default="read", max_length=255)


class WebhookIn(BaseModel):
    url: str = Field(min_length=12, max_length=500)
    events: str = Field(default="abuse.scored", max_length=255)


class MailIn(BaseModel):
    host: str = Field(default="", max_length=255)
    port: int = Field(default=587, ge=1, le=65535)
    username: str = Field(default="", max_length=255)
    password: str = Field(default="", max_length=255)
    sender: str = Field(default="", max_length=255)
    use_tls: bool = True


@router.get("/api/admin/platform/summary")
async def platform_summary(db: AsyncSession = Depends(get_db), admin=Depends(require_permission("read"))):
    plugins = (await db.execute(select(PlatformPlugin).order_by(PlatformPlugin.key))).scalars().all()
    agents = (await db.execute(select(NodeAgent).order_by(NodeAgent.id))).scalars().all()
    violations = (await db.execute(select(AbuseViolation).order_by(AbuseViolation.id.desc()).limit(30))).scalars().all()
    keys = (await db.execute(select(ShopApiKey).order_by(ShopApiKey.id.desc()))).scalars().all()
    hooks = (await db.execute(select(OutboundWebhook).order_by(OutboundWebhook.id.desc()))).scalars().all()
    blacklist = (await db.execute(select(DeviceBlacklist).order_by(DeviceBlacklist.id.desc()).limit(50))).scalars().all()
    countries = (await db.execute(
        select(ConnectionObservation.country, func.count())
        .where(ConnectionObservation.country.is_not(None))
        .group_by(ConnectionObservation.country)
        .order_by(func.count().desc())
        .limit(20)
    )).all()
    return {
        "policy": await _policy(db),
        "plugins": [{"key": p.key, "enabled": p.enabled, "description": p.description} for p in plugins],
        "agents": [{"id": a.id, "name": a.name, "enabled": a.enabled, "cpu": a.cpu, "mem": a.mem, "disk": a.disk, "xray_ok": a.xray_ok, "last_seen_at": a.last_seen_at, "version": a.version} for a in agents],
        "violations": [{"id": v.id, "user_id": v.user_id, "score": v.score, "recommendation": v.recommendation, "summary": v.summary, "status": v.status, "analyzers": v.analyzers, "created_at": v.created_at} for v in violations],
        "api_keys": [{"id": k.id, "name": k.name, "prefix": k.prefix, "scopes": k.scopes, "enabled": k.enabled, "last_used_at": k.last_used_at} for k in keys],
        "webhooks": [{"id": h.id, "url": h.url, "events": h.events, "enabled": h.enabled, "last_status": h.last_status} for h in hooks],
        "blacklist": [{"id": b.id, "hwid": b.hwid, "action": b.action, "note": b.note, "enabled": b.enabled} for b in blacklist],
        "countries": [{"country": c or "—", "count": int(n)} for c, n in countries],
    }


@router.put("/api/admin/platform/policy")
async def save_policy(payload: PolicyIn, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_users"))):
    from .models import AppSetting

    unknown = set(payload.analyzers) - set(ANALYZERS)
    if unknown:
        raise HTTPException(400, "Неизвестный анализатор")
    row = await db.get(AppSetting, "abuse_policy")
    value = json.dumps(payload.model_dump(), ensure_ascii=False)
    if row:
        row.value = value
    else:
        db.add(AppSetting(key="abuse_policy", value=value))
    await db.commit()
    return {"ok": True}


@router.post("/api/admin/platform/plugins/{key}")
async def toggle_plugin(key: str, payload: dict, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_users"))):
    row = (await db.execute(select(PlatformPlugin).where(PlatformPlugin.key == key))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Модуль не найден")
    row.enabled = bool(payload.get("enabled"))
    await db.commit()
    return {"ok": True, "enabled": row.enabled}


@router.post("/api/admin/platform/agents")
async def create_agent(payload: dict, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_users"))):
    await _require_plugin(db, "agent")
    name = str(payload.get("name") or "").strip()[:80]
    if not name:
        raise HTTPException(400, "Укажите имя агента")
    token = secrets.token_urlsafe(32)
    row = NodeAgent(name=name, token_hash=_hash(token), enabled=True, created_at=datetime.utcnow())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": row.id, "name": row.name, "token": token}


@router.post("/api/admin/platform/blacklist")
async def add_blacklist(payload: BlacklistIn, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_users"))):
    row = (await db.execute(select(DeviceBlacklist).where(DeviceBlacklist.hwid == payload.hwid))).scalar_one_or_none()
    if row:
        row.action = payload.action
        row.note = payload.note
        row.enabled = True
    else:
        row = DeviceBlacklist(hwid=payload.hwid, action=payload.action, note=payload.note, enabled=True, created_at=datetime.utcnow())
        db.add(row)
    await db.commit()
    return {"ok": True}


@router.post("/api/admin/platform/violations/{violation_id}/review")
async def review_violation(violation_id: int, payload: dict, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_users"))):
    row = await db.get(AbuseViolation, violation_id)
    if not row:
        raise HTTPException(404, "Нарушение не найдено")
    action = str(payload.get("action") or "reviewed")
    if action not in {"reviewed", "restrict", "clear"}:
        raise HTTPException(400, "Неизвестное действие")
    row.status = "reviewed"
    row.reviewed_at = datetime.utcnow()
    if action == "restrict" and row.user_id:
        user = await db.get(User, row.user_id)
        if user:
            user.restricted_at = datetime.utcnow()
            sub = (await db.execute(select(Subscription).where(Subscription.user_id == user.id))).scalar_one_or_none()
            if sub and sub.remnawave_uuid:
                try:
                    from .remnawave import RemnawaveClient
                    await RemnawaveClient().disable_user(sub.remnawave_uuid)
                except Exception:
                    pass
    if action == "clear" and row.user_id:
        user = await db.get(User, row.user_id)
        if user:
            user.restricted_at = None
    await db.commit()
    return {"ok": True, "status": row.status}


@router.post("/api/admin/platform/api-keys")
async def create_api_key(payload: ApiKeyIn, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("security.manage"))):
    secret = "rw_" + secrets.token_urlsafe(24)
    row = ShopApiKey(name=payload.name, prefix=secret[:10], secret_hash=_hash(secret), scopes=payload.scopes, enabled=True, created_at=datetime.utcnow())
    db.add(row)
    await db.commit()
    return {"id": row.id, "token": secret, "prefix": row.prefix}


@router.delete("/api/admin/platform/api-keys/{key_id}")
async def disable_api_key(key_id: int, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("security.manage"))):
    row = await db.get(ShopApiKey, key_id)
    if not row:
        raise HTTPException(404, "Ключ не найден")
    row.enabled = False
    await db.commit()
    return {"ok": True}


@router.post("/api/admin/platform/webhooks")
async def create_webhook(payload: WebhookIn, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("security.manage"))):
    await _require_plugin(db, "webhooks")
    from .main import validate_public_url

    validate_public_url(payload.url, allow_empty=False)
    secret = secrets.token_urlsafe(24)
    row = OutboundWebhook(url=payload.url, secret_encrypted=encrypt_secret(secret), events=payload.events, enabled=True, created_at=datetime.utcnow())
    db.add(row)
    await db.commit()
    return {"id": row.id, "secret": secret}


@router.put("/api/admin/platform/mail")
async def save_mail(payload: MailIn, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("security.manage"))):
    from .models import AppSetting

    await _require_plugin(db, "mail")
    stored = payload.model_dump()
    if stored["password"]:
        stored["password"] = encrypt_secret(stored["password"])
    else:
        current = await db.get(AppSetting, "smtp_settings")
        if current:
            try:
                stored["password"] = json.loads(current.value).get("password", "")
            except json.JSONDecodeError:
                stored["password"] = ""
    row = await db.get(AppSetting, "smtp_settings")
    value = json.dumps(stored)
    if row:
        row.value = value
    else:
        db.add(AppSetting(key="smtp_settings", value=value))
    await db.commit()
    return {"ok": True}


@router.post("/api/admin/platform/mail/test")
async def test_mail(db: AsyncSession = Depends(get_db), admin=Depends(require_permission("security.manage"))):
    from .models import AppSetting
    from .security import decrypt_secret

    await _require_plugin(db, "mail")
    row = await db.get(AppSetting, "smtp_settings")
    if not row:
        raise HTTPException(400, "SMTP не настроен")
    cfg = json.loads(row.value)
    if not cfg.get("host") or not cfg.get("sender"):
        raise HTTPException(400, "Укажите хост и отправителя")
    password = decrypt_secret(cfg["password"]) if cfg.get("password") else ""
    message = EmailMessage()
    message["From"] = cfg["sender"]
    message["To"] = admin.email
    message["Subject"] = "Remnawave VPN Shop SMTP"
    message.set_content("Проверка исходящей почты. Письмо уходит только администратору, который нажал кнопку.")
    try:
        with smtplib.SMTP(cfg["host"], int(cfg.get("port") or 587), timeout=15) as smtp:
            if cfg.get("use_tls", True):
                smtp.starttls()
            if cfg.get("username"):
                smtp.login(cfg["username"], password)
            smtp.send_message(message)
    except Exception:
        raise HTTPException(502, "SMTP не принял письмо")
    return {"ok": True, "to": admin.email}


@router.post("/api/admin/platform/dkim")
async def create_dkim(payload: dict, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("security.manage"))):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from .models import AppSetting

    selector = str(payload.get("selector") or "shop")[:32]
    domain = str(payload.get("domain") or "")[:255]
    if not domain or "." not in domain:
        raise HTTPException(400, "Укажите домен")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    body = "".join(line for line in public.splitlines() if not line.startswith("-----"))
    txt = f"{selector}._domainkey.{domain} IN TXT \"v=DKIM1; k=rsa; p={body}\""
    row = await db.get(AppSetting, "dkim_private")
    stored = json.dumps({"selector": selector, "domain": domain, "private": encrypt_secret(private)})
    if row:
        row.value = stored
    else:
        db.add(AppSetting(key="dkim_private", value=stored))
    await db.commit()
    return {"txt": txt}


@router.post("/api/agent/heartbeat")
async def agent_heartbeat(payload: HeartbeatIn, db: AsyncSession = Depends(get_db), x_agent_token: str = Header(default="")):
    await _require_plugin(db, "agent")
    agent = await _agent(db, x_agent_token)
    agent.cpu = payload.cpu
    agent.mem = payload.mem
    agent.disk = payload.disk
    agent.xray_ok = payload.xray_ok
    agent.version = payload.version
    agent.last_seen_at = datetime.utcnow()
    actions = (await db.execute(
        select(AgentAction).where(AgentAction.agent_id == agent.id, AgentAction.status == "queued").order_by(AgentAction.id).limit(20)
    )).scalars().all()
    for action in actions:
        if action.kind not in {"throttle", "clear"}:
            action.status = "rejected"
        else:
            action.status = "delivered"
    await db.commit()
    return {"ok": True, "actions": [{"id": a.id, "kind": a.kind, "payload": a.payload} for a in actions if a.status == "delivered"]}


@router.post("/api/agent/observations")
async def agent_observations(payload: ObservationBatch, db: AsyncSession = Depends(get_db), x_agent_token: str = Header(default="")):
    await _require_plugin(db, "agent")
    await _agent(db, x_agent_token)
    if not await _plugin_on(db, "abuse"):
        return {"ok": True, "scored": 0}
    policy = await _policy(db)
    grouped: dict[str, list] = {}
    torrents: set[str] = set()
    now = datetime.utcnow()
    for item in payload.items:
        prefix = source_prefix(item.ip)
        if not prefix:
            continue
        user = None
        if item.remnawave_uuid:
            sub = (await db.execute(select(Subscription).where(Subscription.remnawave_uuid == item.remnawave_uuid))).scalar_one_or_none()
            user = await db.get(User, sub.user_id) if sub else None
        obs = ConnectionObservation(
            user_id=user.id if user else None,
            remnawave_uuid=item.remnawave_uuid,
            ip=item.ip,
            prefix=prefix,
            asn=item.asn,
            asn_org=item.asn_org,
            country=(item.country or "")[:16],
            lat=item.lat,
            lon=item.lon,
            user_agent=item.user_agent,
            hwid=item.hwid,
            mobile=item.mobile,
            torrent=item.torrent and await _plugin_on(db, "torrents"),
            seen_at=now,
        )
        db.add(obs)
        key = str(user.id) if user else (item.hwid or prefix)
        grouped.setdefault(key, []).append({**item.model_dump(), "seen_at": now, "user_id": user.id if user else None})
        if item.torrent:
            torrents.add(key)
    await db.flush()
    created = 0
    for key, rows in grouped.items():
        user_id = rows[0].get("user_id")
        hwid_accounts = 1
        hwid = next((r.get("hwid") for r in rows if r.get("hwid")), None)
        if hwid:
            hwid_accounts = int(await db.scalar(
                select(func.count(func.distinct(ConnectionObservation.user_id))).where(ConnectionObservation.hwid == hwid, ConnectionObservation.user_id.is_not(None))
            ) or 1)
        device_limit = None
        if user_id:
            sub = (await db.execute(select(Subscription).where(Subscription.user_id == user_id))).scalar_one_or_none()
            device_limit = sub.device_limit_snapshot if sub else None
        result = score_observations(rows, device_limit=device_limit, thresholds=policy, hwid_accounts=hwid_accounts, torrent=key in torrents)
        if result["score"] < int(policy["min_score"]):
            continue
        summary = "; ".join(f"{hit['name']}: {hit['detail']}" for hit in result["analyzers"]) or "скоринг"
        violation = AbuseViolation(
            user_id=user_id,
            score=result["score"],
            recommendation=result["recommendation"],
            analyzers={"hits": result["analyzers"], "sources": result["sources"], "addresses": result["addresses"]},
            summary=summary[:2000],
            status="open",
            created_at=now,
        )
        db.add(violation)
        created += 1
        if policy.get("auto_hard_block") and result["score"] >= int(policy["hard_score"]) and user_id:
            user = await db.get(User, user_id)
            if user and not user.restricted_at:
                user.restricted_at = now
        if result["recommendation"] == "throttle" and user_id:
            ips = [r["ip"] for r in rows if source_prefix(r["ip"])]
            agents = (await db.execute(select(NodeAgent).where(NodeAgent.enabled.is_(True)))).scalars().all()
            for agent in agents:
                db.add(AgentAction(agent_id=agent.id, kind="throttle", payload={"ips": ips[:5], "kbps": 1024}, status="queued", created_at=now))
        await _emit(db, "abuse.scored", {"user_id": user_id, "score": result["score"], "recommendation": result["recommendation"]})
    await db.commit()
    return {"ok": True, "scored": created}


async def _emit(db: AsyncSession, event: str, body: dict) -> None:
    if not await _plugin_on(db, "webhooks"):
        return
    from .main import _pinned_public_http_client
    from .security import decrypt_secret

    hooks = (await db.execute(select(OutboundWebhook).where(OutboundWebhook.enabled.is_(True)))).scalars().all()
    raw = json.dumps({"event": event, **body}, ensure_ascii=False).encode()
    for hook in hooks:
        if event not in {part.strip() for part in hook.events.split(",")}:
            continue
        try:
            secret = decrypt_secret(hook.secret_encrypted)
            signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
            async with _pinned_public_http_client(10) as client:
                response = await client.post(hook.url, content=raw, headers={"Content-Type": "application/json", "X-Shop-Signature": signature})
            hook.last_status = str(response.status_code)
            hook.last_error = None if response.status_code < 400 else "delivery failed"
        except Exception:
            hook.last_status = "error"
            hook.last_error = "delivery failed"


@router.get("/api/v3/status")
async def v3_status(request: Request, db: AsyncSession = Depends(get_db)):
    await _api_key(request, db, "read")
    from .main import APP_VERSION
    return {"ok": True, "version": APP_VERSION}


async def _api_key(request: Request, db: AsyncSession, scope: str) -> ShopApiKey:
    header = request.headers.get("authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    if not token:
        raise HTTPException(401, "API-ключ обязателен")
    row = (await db.execute(select(ShopApiKey).where(ShopApiKey.secret_hash == _hash(token), ShopApiKey.enabled.is_(True)))).scalar_one_or_none()
    if not row or scope not in {part.strip() for part in row.scopes.split(",")}:
        raise HTTPException(403, "Недостаточно прав ключа")
    row.last_used_at = datetime.utcnow()
    await db.commit()
    return row


async def prometheus_lines() -> str:
    from .db import SessionLocal

    async with SessionLocal() as db:
        if not await _plugin_on(db, "metrics"):
            return ""
        open_count = int(await db.scalar(select(func.count()).select_from(AbuseViolation).where(AbuseViolation.status == "open")) or 0)
        online_after = datetime.utcnow() - timedelta(minutes=5)
        agents = int(await db.scalar(select(func.count()).select_from(NodeAgent).where(NodeAgent.last_seen_at.is_not(None), NodeAgent.last_seen_at >= online_after)) or 0)
        failed = int(await db.scalar(select(func.count()).select_from(OutboundWebhook).where(OutboundWebhook.last_status == "error")) or 0)
    return f"vpnshop_abuse_open {open_count}\nvpnshop_agents_online {agents}\nvpnshop_webhook_failures {failed}\n"


async def blacklist_decision(db: AsyncSession, hwid: str) -> str | None:
    row = (await db.execute(select(DeviceBlacklist).where(DeviceBlacklist.hwid == hwid, DeviceBlacklist.enabled.is_(True)))).scalar_one_or_none()
    return row.action if row else None
