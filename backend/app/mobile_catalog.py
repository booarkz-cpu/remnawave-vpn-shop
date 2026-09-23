"""Buyer and administrator app cards, plus the logo shown in the cabinet and the apps."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import pathlib
import re
import secrets
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
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
        "file": "",
        "file_label": "",
        "file_sha256": "",
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
        "file": "",
        "file_label": "",
        "file_sha256": "",
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
        "file": "",
        "file_label": "",
        "file_sha256": "",
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
        "file": "",
        "file_label": "",
        "file_sha256": "",
    },
}

# Reference builds published with earlier releases. The shop cabinet serves the
# file an administrator uploaded; these links are the project packages.
OFFICIAL_APPS = (
    {
        "id": "android-user",
        "audience": "user",
        "platform": "android",
        "version": "2.10.0",
        "url": "https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.10.0/remnawave_vpn_shop_android_user_2_10_0.apk",
        "checksum_url": "https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.10.0/remnawave_vpn_shop_android_user_2_10_0.apk.sha256",
    },
    {
        "id": "android-admin",
        "audience": "admin",
        "platform": "android",
        "version": "2.12.0",
        "url": "https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.12.0/remnawave_vpn_shop_android_admin_2_12_0.apk",
        "checksum_url": "https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.12.0/remnawave_vpn_shop_android_admin_2_12_0.apk.sha256",
    },
)

PACKAGE_NAME = re.compile(r"^[a-f0-9]{32}\.(apk|ipa)$")
MAX_PACKAGE_BYTES = 80 * 1024 * 1024

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


def safe_sha256(value: str) -> str:
    text = str(value or "").strip().lower()
    if len(text) == 64 and all(ch in "0123456789abcdef" for ch in text):
        return text
    return ""


def safe_package_name(value: str) -> str:
    name = str(value or "")
    if name != pathlib.Path(name).name or not PACKAGE_NAME.fullmatch(name):
        return ""
    return name


def package_root() -> pathlib.Path:
    from .config import settings

    root = pathlib.Path(settings.media_dir).resolve().parent / "app-packages"
    root.mkdir(parents=True, exist_ok=True)
    return root


def package_path(name: str) -> pathlib.Path | None:
    safe = safe_package_name(name)
    if not safe:
        return None
    root = package_root().resolve()
    path = (root / safe).resolve()
    if path.parent != root:
        return None
    return path


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
        "file": "",
        "file_label": "",
        "file_sha256": "",
    }


def attach_stored_file(card: dict, raw: dict) -> dict:
    name = safe_package_name(str(raw.get("file") or ""))
    card["file"] = name
    card["file_label"] = _clip(str(raw.get("file_label") or ""), 80, "") if name else ""
    card["file_sha256"] = safe_sha256(str(raw.get("file_sha256") or "")) if name else ""
    return card


def view_card(card: dict, *, public: bool) -> dict:
    shown = {key: card[key] for key in ("id", "audience", "platform", "enabled", "title_ru", "title_en", "text_ru", "text_en", "url")}
    visible = bool(card.get("file")) and (not public or (card.get("audience") == "user" and card.get("enabled")))
    if visible:
        prefix = "/api/public/apps" if public else "/api/admin/apps"
        shown["download_url"] = f"{prefix}/{card['id']}/download"
        shown["sha256"] = safe_sha256(str(card.get("file_sha256") or ""))
    else:
        shown["download_url"] = ""
        shown["sha256"] = ""
    if not public:
        shown["has_file"] = bool(card.get("file"))
        shown["file_label"] = card.get("file_label") or ""
    return shown


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
            card = attach_stored_file(card_from_input(row), row)
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
    shown = public_cards(cards) if public else cards
    body = {"logo_url": safe_media_path(values.get(LOGO_KEY, "")), "apps": [view_card(card, public=public) for card in shown]}
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

    current = {card["id"]: card for card in parse_catalog((await _settings(db)).get(CATALOG_KEY))}
    seen: list[dict] = []
    ids: list[str] = []
    for item in payload.apps:
        try:
            card = card_from_input(item.model_dump())
        except ValueError as exc:
            if str(exc) == "url":
                raise HTTPException(400, "Нужна https-ссылка без логина и локального адреса")
            raise HTTPException(400, "Неизвестное приложение")
        previous = current.get(card["id"], {})
        card["file"] = safe_package_name(str(previous.get("file") or ""))
        card["file_label"] = previous.get("file_label") or "" if card["file"] else ""
        card["file_sha256"] = safe_sha256(str(previous.get("file_sha256") or "")) if card["file"] else ""
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
async def upload_client_logo(admin=Depends(require_permission("manage_content")), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
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


def _download_name(app_id: str, stored: str) -> str:
    suffix = ".ipa" if stored.endswith(".ipa") else ".apk"
    return f"remnawave-{app_id}{suffix}"


def _media_type(stored: str) -> str:
    if stored.endswith(".apk"):
        return "application/vnd.android.package-archive"
    return "application/octet-stream"


async def _read_package(file: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(min(1024 * 1024, MAX_PACKAGE_BYTES - total + 1))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_PACKAGE_BYTES:
            raise HTTPException(413, "Файл приложения слишком большой")
    return b"".join(chunks)


def _package_response(card: dict) -> FileResponse:
    path = package_path(str(card.get("file") or ""))
    if path is None or not path.is_file():
        raise HTTPException(404, "Файл не найден")
    stored = path.name
    return FileResponse(path, media_type=_media_type(stored), filename=_download_name(card["id"], stored))


async def _write_catalog(db: AsyncSession, cards: list[dict]) -> None:
    ordered = {card["id"]: card for card in cards}
    encoded = json.dumps([ordered[app_id] for app_id in APP_IDS], ensure_ascii=False)
    row = await db.get(AppSetting, CATALOG_KEY)
    if row:
        row.value = encoded
    else:
        db.add(AppSetting(key=CATALOG_KEY, value=encoded))


@router.post("/api/admin/apps/{app_id}/file")
async def upload_app_file(app_id: str, admin=Depends(require_permission("manage_content")), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    from .main import audit

    if app_id not in APP_IDS:
        raise HTTPException(404, "Неизвестное приложение")
    ext = ".apk" if app_id.startswith("android-") else ".ipa"
    original = pathlib.Path(file.filename or "").name.lower()
    if not original.endswith(ext):
        raise HTTPException(400, "Для Android нужен APK, для iOS нужен IPA")
    data = await _read_package(file)
    if not data.startswith(b"PK\x03\x04"):
        raise HTTPException(400, "Файл не похож на пакет приложения")
    digest = hashlib.sha256(data).hexdigest()
    name = secrets.token_hex(16) + ext
    path = package_path(name)
    if path is None:
        raise HTTPException(500, "Файл не сохранён")
    path.write_bytes(data)
    cards = parse_catalog((await _settings(db)).get(CATALOG_KEY))
    previous = ""
    for card in cards:
        if card["id"] != app_id:
            continue
        previous = card.get("file") or ""
        card["file"] = name
        card["file_label"] = ext.removeprefix(".")
        card["file_sha256"] = digest
    try:
        await _write_catalog(db, cards)
        await audit(db, "content.apps.file.updated", admin.email, app_id)
        await db.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    old = package_path(previous)
    if old and old != path:
        old.unlink(missing_ok=True)
    return await catalog_payload(db, public=False)


@router.delete("/api/admin/apps/{app_id}/file")
async def delete_app_file(app_id: str, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_content"))):
    from .main import audit

    if app_id not in APP_IDS:
        raise HTTPException(404, "Неизвестное приложение")
    cards = parse_catalog((await _settings(db)).get(CATALOG_KEY))
    removed = ""
    for card in cards:
        if card["id"] != app_id:
            continue
        removed = card.get("file") or ""
        card["file"] = ""
        card["file_label"] = ""
        card["file_sha256"] = ""
    await _write_catalog(db, cards)
    await audit(db, "content.apps.file.deleted", admin.email, app_id)
    await db.commit()
    old = package_path(removed)
    if old:
        old.unlink(missing_ok=True)
    return await catalog_payload(db, public=False)


@router.get("/api/public/apps/install")
async def public_install_guide(db: AsyncSession = Depends(get_db)):
    catalog = await catalog_payload(db, public=True)
    return {
        "shop_apps": catalog["apps"],
        "official": list(OFFICIAL_APPS),
        "steps_ru": [
            "Покупатель Android: в личном кабинете откройте блок «Приложения» и нажмите «Скачать», либо откройте GET /api/public/apps/android-user/download, если администратор загрузил APK.",
            "Покупатель iOS: та же карточка ведёт на GET /api/public/apps/ios-user/download, если администратор загрузил IPA. Готового IPA в релизах GitHub нет.",
            "Сборка проекта для Android покупателя 2.10.0 и администратора 2.12.0 лежит на GitHub. Рядом с APK есть файл .sha256. Проверка: sha256sum -c имя.apk.sha256 в каталоге, где лежат оба файла.",
            "На Android разрешите установку из выбранного источника и откройте APK. На iOS пакет подписывают в Xcode на macOS из mobile/ios-user или mobile/ios-admin.",
        ],
        "steps_en": [
            "Android buyer: in the user cabinet open Apps and press Download, or open GET /api/public/apps/android-user/download when an administrator has uploaded an APK.",
            "iOS buyer: the same card leads to GET /api/public/apps/ios-user/download when an administrator has uploaded an IPA. GitHub releases do not include an IPA.",
            "The project Android builds stay at buyer 2.10.0 and administrator 2.12.0 on GitHub. A .sha256 file sits next to each APK. Check it with sha256sum -c name.apk.sha256 in the directory that holds both files.",
            "On Android, allow installation from the source you chose and open the APK. On iOS, sign the package in Xcode on macOS from mobile/ios-user or mobile/ios-admin.",
        ],
    }


@router.get("/api/public/apps/{app_id}/download")
async def public_app_download(app_id: str, db: AsyncSession = Depends(get_db)):
    if app_id not in APP_IDS:
        raise HTTPException(404, "Файл не найден")
    card = next((item for item in parse_catalog((await _settings(db)).get(CATALOG_KEY)) if item["id"] == app_id), None)
    if not card or card.get("audience") != "user" or not card.get("enabled") or not card.get("file"):
        raise HTTPException(404, "Файл не найден")
    return _package_response(card)


@router.get("/api/admin/apps/{app_id}/download")
async def admin_app_download(app_id: str, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("read"))):
    if app_id not in APP_IDS:
        raise HTTPException(404, "Файл не найден")
    card = next((item for item in parse_catalog((await _settings(db)).get(CATALOG_KEY)) if item["id"] == app_id), None)
    if not card or not card.get("file"):
        raise HTTPException(404, "Файл не найден")
    return _package_response(card)
