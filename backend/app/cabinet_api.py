"""Cabinet auth, public menu and admin CMS routes for version 2.4.0."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text as sql_text

from .config import settings
from .db import get_db
from .models import AppSetting, AuthExchangeCode, CabinetMenuItem, Payment, User
from .security import hash_password, verify_password, require_permission

router = APIRouter()


class EmailAuthIn(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    username: str | None = Field(default=None, max_length=255)


class CabinetMenuIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9_-]+$")
    kind: str = Field(default="custom", pattern="^(overview|plans|trial|connection|support|servers|custom)$")
    body: str = Field(default="", max_length=20000)
    sort_order: int = Field(default=0, ge=-10000, le=10000)
    enabled: bool = True


class GuideIn(BaseModel):
    value: str = Field(default="", max_length=100000)


def _normalize_email(value: str) -> str:
    email = (value or "").strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Invalid email")
    return email


def _client_ip(request: Request) -> str:
    return (request.headers.get("x-forwarded-for") or request.client.host if request.client else "")[:64]


@router.post("/api/auth/register")
async def auth_register(payload: EmailAuthIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    from .main import create_user_session, _set_auth_cookies, audit
    from .mobile_auth import require_mobile_proof
    require_mobile_proof(request)

    email = _normalize_email(payload.email)
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    user = User(
        email=email,
        email_password_hash=hash_password(payload.password),
        username=(payload.username or email.split("@")[0])[:255],
        referral_code=secrets.token_urlsafe(8).upper(),
    )
    db.add(user)
    await db.flush()
    token = await create_user_session(db, user, request)
    await audit(db, "auth.user.register", f"user:{user.id}", None, {"method": "email", "ip": _client_ip(request)})
    await db.commit()
    from .mobile_auth import mobile_client_name, session_body

    body = {"id": user.id, "email": user.email, "username": user.username}
    if mobile_client_name(request):
        return session_body(request, token, body)
    response.set_cookie("rw_user", token, httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite, max_age=3600)
    _set_auth_cookies(response, token)
    return body


@router.post("/api/auth/login")
async def auth_login(payload: EmailAuthIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    from .main import create_user_session, _set_auth_cookies, audit
    from .mobile_auth import require_mobile_proof
    require_mobile_proof(request)

    email = _normalize_email(payload.email)
    user = (await db.execute(select(User).where(User.email == email).with_for_update())).scalar_one_or_none()
    if not user or user.deleted_at is not None or not user.email_password_hash or not verify_password(payload.password, user.email_password_hash):
        raise HTTPException(401, "Invalid email or password")
    token = await create_user_session(db, user, request)
    await audit(db, "auth.user.login", f"user:{user.id}", None, {"method": "email", "ip": _client_ip(request)})
    await db.commit()
    from .mobile_auth import mobile_client_name, session_body

    body = {"id": user.id, "email": user.email, "username": user.username}
    if mobile_client_name(request):
        return session_body(request, token, body)
    response.set_cookie("rw_user", token, httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite, max_age=3600)
    _set_auth_cookies(response, token)
    return body


@router.get("/api/auth/vk")
async def vk_login(request: Request):
    if not settings.vk_client_id or not settings.vk_redirect_uri:
        raise HTTPException(503, "VK ID is not configured")
    state = __import__("jwt").encode(
        {"typ": "vk_oauth", "nonce": secrets.token_urlsafe(12), "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp())},
        settings.app_secret,
        algorithm="HS256",
    )
    params = urllib.parse.urlencode(
        {"response_type": "code", "client_id": settings.vk_client_id, "redirect_uri": settings.vk_redirect_uri, "state": state, "scope": "email", "v": "5.199"}
    )
    resp = RedirectResponse("https://oauth.vk.com/authorize?" + params)
    resp.set_cookie("vk_oauth_state", state, httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=600)
    return resp


@router.get("/api/auth/vk/callback")
async def vk_callback(code: str, state: str, request: Request, db: AsyncSession = Depends(get_db)):
    from .main import _pinned_public_http_client, audit

    try:
        if not request.cookies.get("vk_oauth_state") or not hmac.compare_digest(request.cookies["vk_oauth_state"], state):
            raise ValueError()
        __import__("jwt").decode(state, settings.app_secret, algorithms=["HS256"])
    except Exception:
        raise HTTPException(400, "Invalid OAuth state")
    if not settings.vk_client_secret:
        raise HTTPException(503, "VK ID secret is not configured")
    async with _pinned_public_http_client(20) as client:
        token_r = await client.get(
            "https://oauth.vk.com/access_token",
            params={"client_id": settings.vk_client_id, "client_secret": settings.vk_client_secret, "redirect_uri": settings.vk_redirect_uri, "code": code},
        )
        token_r.raise_for_status()
        token_data = token_r.json()
    vk_user_id = str(token_data.get("user_id") or "")
    if not vk_user_id:
        raise HTTPException(400, "VK did not return a user id")
    email = (token_data.get("email") or "").strip().lower() or None
    await db.execute(sql_text("SELECT pg_advisory_xact_lock(:key)"), {"key": 1200000000 + (int(hashlib.sha256(vk_user_id.encode()).hexdigest()[:8], 16) % 900000000)})
    user = (await db.execute(select(User).where(User.vk_id == vk_user_id))).scalar_one_or_none()
    if not user and email:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user:
            user.vk_id = vk_user_id
    if not user:
        user = User(vk_id=vk_user_id, email=email, username=f"vk_{vk_user_id}", referral_code=secrets.token_urlsafe(8).upper())
        db.add(user)
        await db.flush()
    await db.commit()
    await db.refresh(user)
    raw = secrets.token_urlsafe(32)
    db.add(AuthExchangeCode(code_hash=hashlib.sha256(raw.encode()).hexdigest(), user_id=user.id, expires_at=datetime.utcnow() + timedelta(minutes=5)))
    await audit(db, "auth.user.login", f"user:{user.id}", None, {"method": "vk", "ip": _client_ip(request)})
    await db.commit()
    dest = (settings.cabinet_url or settings.mini_app_url or "/").rstrip("/")
    resp = RedirectResponse(f"{dest}/?code=" + urllib.parse.quote(raw))
    resp.delete_cookie("vk_oauth_state")
    return resp


@router.get("/api/public/cabinet-menu")
async def public_cabinet_menu(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(CabinetMenuItem).where(CabinetMenuItem.enabled.is_(True)).order_by(CabinetMenuItem.sort_order, CabinetMenuItem.id))).scalars().all()
    if not rows:
        return [
            {"slug": "overview", "title": "Обзор", "kind": "overview", "body": ""},
            {"slug": "plans", "title": "Тарифы", "kind": "plans", "body": ""},
            {"slug": "trial", "title": "Пробный период", "kind": "trial", "body": ""},
            {"slug": "connection", "title": "Подключение", "kind": "connection", "body": ""},
            {"slug": "support", "title": "Поддержка", "kind": "support", "body": ""},
        ]
    return [{"id": x.id, "slug": x.slug, "title": x.title, "kind": x.kind, "body": x.body, "sort_order": x.sort_order} for x in rows]


@router.post("/api/payments/sandbox/complete")
async def sandbox_complete(payload: dict, request: Request, db: AsyncSession = Depends(get_db)):
    from .main import user_from_token, fulfill

    if not settings.payments_sandbox:
        raise HTTPException(404, "Not found")
    user = await user_from_token(request, db)
    payment_id = str(payload.get("payment_id") or "")
    order_id = str(payload.get("order_id") or "")
    q = select(Payment).where(Payment.user_id == user.id, Payment.provider == "sandbox")
    if payment_id:
        q = q.where(Payment.provider_payment_id == payment_id)
    elif order_id:
        q = q.where(Payment.order_id == order_id)
    else:
        raise HTTPException(400, "payment_id or order_id required")
    payment = (await db.execute(q.order_by(Payment.id.desc()).with_for_update())).scalar_one_or_none()
    if not payment:
        raise HTTPException(404, "Sandbox payment not found")
    if payment.status != "paid":
        payment.status = "paid"
        payment.paid_at = datetime.utcnow()
        await db.commit()
    await fulfill(payment.id, db)
    payment = await db.get(Payment, payment.id)
    return {"ok": True, "payment_id": payment.id, "fulfillment_status": payment.fulfillment_status}


@router.get("/api/admin/cabinet/menu")
async def admin_cabinet_menu(db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_content"))):
    rows = (await db.execute(select(CabinetMenuItem).order_by(CabinetMenuItem.sort_order, CabinetMenuItem.id))).scalars().all()
    return [{"id": x.id, "title": x.title, "slug": x.slug, "kind": x.kind, "body": x.body, "sort_order": x.sort_order, "enabled": x.enabled} for x in rows]


@router.post("/api/admin/cabinet/menu")
async def admin_cabinet_menu_create(payload: CabinetMenuIn, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_content"))):
    from .main import audit

    if await db.scalar(select(CabinetMenuItem.id).where(CabinetMenuItem.slug == payload.slug)):
        raise HTTPException(409, "Slug already exists")
    x = CabinetMenuItem(**payload.model_dump())
    db.add(x)
    await audit(db, "cabinet.menu.created", admin.email, payload.slug)
    await db.commit()
    await db.refresh(x)
    return {"id": x.id}


@router.put("/api/admin/cabinet/menu/{item_id}")
async def admin_cabinet_menu_update(item_id: int, payload: CabinetMenuIn, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_content"))):
    from .main import audit

    x = await db.get(CabinetMenuItem, item_id)
    if not x:
        raise HTTPException(404, "Not found")
    clash = await db.scalar(select(CabinetMenuItem.id).where(CabinetMenuItem.slug == payload.slug, CabinetMenuItem.id != item_id))
    if clash:
        raise HTTPException(409, "Slug already exists")
    for k, v in payload.model_dump().items():
        setattr(x, k, v)
    await audit(db, "cabinet.menu.updated", admin.email, str(item_id))
    await db.commit()
    return {"ok": True}


@router.delete("/api/admin/cabinet/menu/{item_id}")
async def admin_cabinet_menu_delete(item_id: int, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_content"))):
    from .main import audit

    x = await db.get(CabinetMenuItem, item_id)
    if not x:
        raise HTTPException(404, "Not found")
    await db.delete(x)
    await audit(db, "cabinet.menu.deleted", admin.email, str(item_id))
    await db.commit()
    return {"ok": True}


@router.get("/api/admin/cabinet/guides")
async def admin_cabinet_guides(db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_content"))):
    platforms = ("android", "ios", "tv", "windows", "macos", "linux")
    out = {}
    for platform in platforms:
        row = await db.get(AppSetting, f"guide_{platform}")
        out[platform] = row.value if row else ""
    return out


@router.put("/api/admin/cabinet/guides/{platform}")
async def admin_cabinet_guide(platform: str, payload: GuideIn, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_content"))):
    from .main import audit

    if platform not in {"android", "ios", "tv", "windows", "macos", "linux"}:
        raise HTTPException(400, "Unsupported platform")
    key = f"guide_{platform}"
    row = await db.get(AppSetting, key)
    if not row:
        row = AppSetting(key=key, value=payload.value)
        db.add(row)
    else:
        row.value = payload.value
    await audit(db, "cabinet.guide.updated", admin.email, platform)
    await db.commit()
    return {"ok": True}
