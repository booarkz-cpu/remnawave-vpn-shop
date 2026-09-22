"""Buyer and administrator app cards, plus the logo shown in the cabinet and the apps."""
from __future__ import annotations

import ipaddress
import json
import pathlib
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models import AppSetting
from .security import require_permission

CATALOG_KEY = "mobile_apps"
LOGO_KEY = "client_logo"
APP_IDS = ("android-user", "ios-user", "android-admin", "ios-admin")

DEFAULTS: dict[str, dict] = {
    "android-user": {
        "id": "android-user",
        "audience": "user",
        "platform": "android",
        "enabled": True,
        "title_ru": "Приложение для Android",
        "title_en": "Android app",
        "text_ru": "Покупатель управляет подпиской, тарифами и подключением в отдельном приложении.",
        "text_en": "The buyer manages the subscription, plans and connection in a separate app.",
        "url": "",
    },
    "ios-user": {
        "id": "ios-user",
        "audience": "user",
        "platform": "ios",
        "enabled": True,
        "title_ru": "Приложение для iOS",
        "title_en": "iOS app",
        "text_ru": "Покупатель открывает магазин на iPhone и iPad.",
        "text_en": "The buyer opens the shop on iPhone and iPad.",
        "url": "",
    },
    "android-admin": {
        "id": "android-admin",
        "audience": "admin",
        "platform": "android",
        "enabled": True,
        "title_ru": "Админ-приложение Android",
        "title_en": "Android admin app",
        "text_ru": "Администратор смотрит платежи, мониторинг и нарушения.",
        "text_en": "The administrator reviews payments, monitoring and violations.",
        "url": "",
    },
    "ios-admin": {
        "id": "ios-admin",
        "audience": "admin",
        "platform": "ios",
        "enabled": True,
        "title_ru": "Админ-приложение iOS",
        "title_en": "iOS admin app",
        "text_ru": "Администратор открывает панель на iPhone и iPad.",
        "text_en": "The administrator opens the console on iPhone and iPad.",
        "url": "",
    },
}

router = APIRouter()


def safe_media_path(value: str) -> str:
    raw = (value or "").strip()
    if not raw.startswith("/media/"):
        return ""
    name = raw.removeprefix("/media/")
    if not name or any(ch in name for ch in "/\\?#") or ".." in name or name != pathlib.Path(name).name:
        return ""
    return "/media/" + name


def normalize_store_url(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if any(ch.isspace() for ch in raw) or len(raw) > 500:
        raise ValueError("url")
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or parsed.username or parsed.password or not host:
        raise ValueError("url")
    if host in {"localhost", "127.0.0.1", "10.0.2.2"} or host.endswith(".localhost"):
        raise ValueError("url")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast):
        raise ValueError("url")
    return raw


def _clip(value: str, limit: int, fallback: str) -> str:
    text = " ".join((value or "").split())
    if not text:
        return fallback
    return text[:limit]


def card_from_input(raw: dict) -> dict:
    app_id = str(raw.get("id") or "")
    if app_id not in DEFAULTS:
        raise ValueError("id")
    base = DEFAULTS[app_id]
    return {
        "id": app_id,
        "audience": base["audience"],
        "platform": base["platform"],
        "enabled": bool(raw.get("enabled", True)),
        "title_ru": _clip(str(raw.get("title_ru") or ""), 120, base["title_ru"]),
        "title_en": _clip(str(raw.get("title_en") or ""), 120, base["title_en"]),
        "text_ru": _clip(str(raw.get("text_ru") or ""), 500, base["text_ru"]),
        "text_en": _clip(str(raw.get("text_en") or ""), 500, base["text_en"]),
        "url": normalize_store_url(str(raw.get("url") or "")),
    }


def parse_catalog(raw: str | None) -> list[dict]:
    found: dict[str, dict] = {}
    try:
        payload = json.loads(raw or "[]")
    except json.JSONDecodeError:
        payload = []
    rows = payload if isinstance(payload, list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            card = card_from_input(row)
        except ValueError:
            continue
        found[card["id"]] = card
    return [found.get(app_id, dict(DEFAULTS[app_id])) for app_id in APP_IDS]


def public_cards(cards: list[dict]) -> list[dict]:
    return [card for card in cards if card.get("audience") == "user" and card.get("enabled")]


class AppCardIn(BaseModel):
    id: str
    enabled: bool = True
    title_ru: str = Field(default="", max_length=120)
    title_en: str = Field(default="", max_length=120)
    text_ru: str = Field(default="", max_length=500)
    text_en: str = Field(default="", max_length=500)
    url: str = Field(default="", max_length=500)


class AppsIn(BaseModel):
    apps: list[AppCardIn] = Field(max_length=8)


async def _settings(db: AsyncSession) -> dict[str, str]:
    rows = (await db.execute(select(AppSetting).where(AppSetting.key.in_({CATALOG_KEY, LOGO_KEY})))).scalars().all()
    return {row.key: row.value for row in rows}


async def catalog_payload(db: AsyncSession, *, public: bool) -> dict:
    values = await _settings(db)
    cards = parse_catalog(values.get(CATALOG_KEY))
    body = {"logo_url": safe_media_path(values.get(LOGO_KEY, "")), "apps": public_cards(cards) if public else cards}
    return body


@router.get("/api/public/apps")
async def public_apps(db: AsyncSession = Depends(get_db)):
    return await catalog_payload(db, public=True)


@router.get("/api/admin/apps")
async def admin_apps(db: AsyncSession = Depends(get_db), admin=Depends(require_permission("read"))):
    return await catalog_payload(db, public=False)


@router.put("/api/admin/apps")
async def save_apps(payload: AppsIn, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_content"))):
    from .main import audit

    seen: list[dict] = []
    ids: list[str] = []
    for item in payload.apps:
        try:
            card = card_from_input(item.model_dump())
        except ValueError as exc:
            if str(exc) == "url":
                raise HTTPException(400, "Нужна https-ссылка без логина и локального адреса")
            raise HTTPException(400, "Неизвестное приложение")
        if card["id"] in ids:
            raise HTTPException(400, "Приложение указано дважды")
        ids.append(card["id"])
        seen.append(card)
    if set(ids) != set(APP_IDS):
        raise HTTPException(400, "Нужны все четыре приложения")
    ordered = {card["id"]: card for card in seen}
    encoded = json.dumps([ordered[app_id] for app_id in APP_IDS], ensure_ascii=False)
    row = await db.get(AppSetting, CATALOG_KEY)
    if row:
        row.value = encoded
    else:
        db.add(AppSetting(key=CATALOG_KEY, value=encoded))
    await audit(db, "content.apps.updated", admin.email)
    await db.commit()
    return await catalog_payload(db, public=False)


@router.post("/api/admin/apps/logo")
async def upload_client_logo(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_content"))):
    from .main import _replace_branding_file, _store_branding_image, audit

    url = await _store_branding_image(file, "client-logo")
    await _replace_branding_file(db, LOGO_KEY, url)
    await audit(db, "content.apps.logo.updated", admin.email)
    await db.commit()
    return {"ok": True, "logo_url": url}


@router.delete("/api/admin/apps/logo")
async def delete_client_logo(db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_content"))):
    from .config import settings
    from .main import audit

    row = await db.get(AppSetting, LOGO_KEY)
    if row and row.value.startswith("/media/"):
        name = safe_media_path(row.value).removeprefix("/media/")
        if name:
            try:
                pathlib.Path(settings.media_dir, name).unlink(missing_ok=True)
            except Exception:
                pass
        row.value = ""
    await audit(db, "content.apps.logo.deleted", admin.email)
    await db.commit()
    return {"ok": True, "logo_url": ""}
