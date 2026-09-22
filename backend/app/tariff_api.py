"""Tariff constructor and Remnawave node status for version 2.5.0."""
from __future__ import annotations

import re
import time
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models import Plan, TariffConstructor, TariffConstructorOption
from .security import require_permission

router = APIRouter()
KINDS = ("devices", "traffic_gb", "days")
_HOSTISH = re.compile(r"(https?://)|(\d{1,3}(?:\.\d{1,3}){3})|([a-z0-9-]+\.[a-z]{2,})", re.I)
_SECRET_KEYS = {"address", "host", "hostname", "ip", "port", "token", "secret", "password", "url", "config"}


class OptionIn(BaseModel):
    kind: str = Field(pattern="^(devices|traffic_gb|days)$")
    label: str = Field(min_length=1, max_length=255)
    value: int = Field(ge=0, le=3650)
    price: Decimal = Field(ge=0, le=1000000, decimal_places=2, max_digits=12)
    enabled: bool = True
    sort_order: int = Field(default=0, ge=-10000, le=10000)


class ConstructorIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=4000)
    base_price: Decimal = Field(ge=0, le=1000000, decimal_places=2, max_digits=12)
    enabled: bool = True
    remnawave_profile_id: str | None = Field(default=None, max_length=255)
    sort_order: int = Field(default=0, ge=-10000, le=10000)
    options: list[OptionIn] = Field(default_factory=list, max_length=60)


def _money(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _validate_options(options: list[OptionIn], enabled: bool) -> None:
    for opt in options:
        if opt.kind == "devices" and not 1 <= opt.value <= 100:
            raise HTTPException(400, "Количество устройств должно быть от 1 до 100")
        if opt.kind == "days" and not 1 <= opt.value <= 3650:
            raise HTTPException(400, "Срок подписки должен быть от 1 до 3650 дней")
        if opt.kind == "traffic_gb" and opt.value > 100000:
            raise HTTPException(400, "Лимит трафика слишком большой")
    if enabled:
        kinds = {opt.kind for opt in options if opt.enabled}
        missing = [k for k in KINDS if k not in kinds]
        if missing:
            raise HTTPException(400, "Для каждого пункта нужен хотя бы один включённый вариант: устройства, трафик, дни")


def _option_out(opt: TariffConstructorOption) -> dict:
    return {
        "id": opt.id,
        "kind": opt.kind,
        "label": opt.label,
        "value": opt.value,
        "price": float(opt.price),
        "enabled": opt.enabled,
        "sort_order": opt.sort_order,
    }


def _constructor_out(row: TariffConstructor, options: list[TariffConstructorOption]) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "base_price": float(row.base_price),
        "plan_id": row.plan_id,
        "remnawave_profile_id": row.remnawave_profile_id,
        "enabled": row.enabled,
        "sort_order": row.sort_order,
        "options": [_option_out(o) for o in options],
    }


async def _options(db: AsyncSession, constructor_id: int) -> list[TariffConstructorOption]:
    return list((await db.execute(
        select(TariffConstructorOption)
        .where(TariffConstructorOption.constructor_id == constructor_id)
        .order_by(TariffConstructorOption.sort_order, TariffConstructorOption.id)
    )).scalars().all())


def _sync_plan(plan: Plan, row: TariffConstructor, options: list[TariffConstructorOption]) -> None:
    days = next((o.value for o in options if o.kind == "days" and o.enabled), 30)
    traffic = next((o.value for o in options if o.kind == "traffic_gb" and o.enabled), None)
    devices = next((o.value for o in options if o.kind == "devices" and o.enabled), None)
    plan.name = row.name
    plan.price = row.base_price
    plan.duration_days = max(1, int(days or 30))
    plan.traffic_limit_gb = None if traffic in (None, 0) else int(traffic)
    plan.device_limit = int(devices) if devices else None
    plan.remnawave_profile_id = row.remnawave_profile_id
    plan.enabled = row.enabled


async def quote_constructor(db: AsyncSession, payload: dict) -> dict:
    try:
        constructor_id = int(payload.get("constructor_id"))
        picked = {
            "devices": int(payload.get("device_option_id")),
            "traffic_gb": int(payload.get("traffic_option_id")),
            "days": int(payload.get("days_option_id")),
        }
    except (TypeError, ValueError):
        raise HTTPException(400, "Выберите устройства, трафик и срок")
    row = await db.get(TariffConstructor, constructor_id)
    if not row or not row.enabled or not row.plan_id:
        raise HTTPException(404, "Конструктор тарифа не найден")
    options = {o.id: o for o in await _options(db, row.id)}
    selected = {}
    for kind, option_id in picked.items():
        opt = options.get(option_id)
        if not opt or opt.kind != kind or not opt.enabled:
            raise HTTPException(400, "Выбран недоступный пункт конструктора")
        selected[kind] = opt
    amount = _money(Decimal(str(row.base_price)) + sum(Decimal(str(o.price)) for o in selected.values()))
    if amount <= 0:
        raise HTTPException(400, "Сумма конструктора должна быть больше нуля")
    traffic = selected["traffic_gb"].value
    return {
        "constructor_id": row.id,
        "plan_id": row.plan_id,
        "amount": amount,
        "days": int(selected["days"].value),
        "traffic_gb": None if traffic == 0 else int(traffic),
        "devices": int(selected["devices"].value),
        "profile_id": row.remnawave_profile_id,
        "name": row.name,
    }


def _iter_nodes(payload) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("response", "nodes", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        if isinstance(value, dict):
            inner = value.get("nodes") or value.get("items")
            if isinstance(inner, list):
                return [x for x in inner if isinstance(x, dict)]
    return []


def public_node(node: dict) -> dict:
    disabled = node.get("isDisabled")
    connected = node.get("isConnected")
    if disabled is True:
        status = "disabled"
    elif connected is True:
        status = "online"
    elif connected is False:
        status = "offline"
    else:
        raw = str(node.get("status") or "unknown").lower()
        status = raw if raw in {"online", "offline", "disabled", "unknown"} else "unknown"
    country = str(node.get("countryCode") or node.get("country") or "")[:16]
    if _HOSTISH.search(country):
        country = ""
    raw_name = str(node.get("name") or "node")
    name = "node" if _HOSTISH.search(raw_name) else raw_name[:80]
    safe = {
        "name": name,
        "country": country,
        "status": status,
        "users_online": node.get("usersOnline") if isinstance(node.get("usersOnline"), int) else None,
    }
    leaked = _SECRET_KEYS.intersection(safe)
    if leaked:
        raise RuntimeError("public node payload contained a secret field")
    return safe


async def linked_constructor_id(db: AsyncSession, plan_id: int) -> int | None:
    return await db.scalar(select(TariffConstructor.id).where(TariffConstructor.plan_id == plan_id))


async def remnawave_server_status(scope: str) -> dict:
    from .remnawave import RemnawaveClient

    started = time.perf_counter()
    try:
        raw = await RemnawaveClient().list_nodes(start=0, size=200)
        nodes = [public_node(n) for n in _iter_nodes(raw)]
        return {
            "ok": True,
            "scope": scope,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "total": len(nodes),
            "online": sum(n["status"] == "online" for n in nodes),
            "offline": sum(n["status"] == "offline" for n in nodes),
            "disabled": sum(n["status"] == "disabled" for n in nodes),
            "nodes": nodes,
        }
    except Exception:
        return {
            "ok": False,
            "scope": scope,
            "latency_ms": None,
            "total": 0,
            "online": 0,
            "offline": 0,
            "disabled": 0,
            "nodes": [],
            "error": "Remnawave недоступен",
        }


@router.get("/api/tariff-constructors")
async def public_constructors(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(TariffConstructor).where(TariffConstructor.enabled.is_(True)).order_by(TariffConstructor.sort_order, TariffConstructor.id)
    )).scalars().all()
    out = []
    for row in rows:
        options = [o for o in await _options(db, row.id) if o.enabled]
        if {o.kind for o in options} >= set(KINDS):
            out.append(_constructor_out(row, options))
    return out


@router.get("/api/public/servers")
async def public_servers():
    return await remnawave_server_status("public")


@router.get("/api/me/servers")
async def my_servers(request: Request, db: AsyncSession = Depends(get_db)):
    from .main import user_from_token
    from .models import Subscription

    user = await user_from_token(request, db)
    status = await remnawave_server_status("user")
    sub = (await db.execute(select(Subscription).where(Subscription.user_id == user.id))).scalar_one_or_none()
    now = datetime.utcnow()
    lifecycle = (sub.lifecycle_status if sub else "") or ""
    status["subscription_active"] = bool(
        sub and sub.expires_at and sub.expires_at > now and lifecycle not in {"expired", "cancelled"}
    )
    return status


@router.get("/api/admin/remnawave/monitoring")
async def admin_monitoring(admin=Depends(require_permission("read"))):
    status = await remnawave_server_status("admin")
    status["checked_by"] = admin.email
    return status


@router.get("/api/admin/tariff-constructors")
async def admin_constructors(db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_plans"))):
    rows = (await db.execute(select(TariffConstructor).order_by(TariffConstructor.sort_order, TariffConstructor.id))).scalars().all()
    return [_constructor_out(row, await _options(db, row.id)) for row in rows]


@router.post("/api/admin/tariff-constructors")
async def admin_constructor_create(payload: ConstructorIn, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_plans"))):
    from .main import audit

    _validate_options(payload.options, payload.enabled)
    plan = Plan(name=payload.name, price=payload.base_price, duration_days=30, enabled=payload.enabled, remnawave_profile_id=payload.remnawave_profile_id)
    db.add(plan)
    await db.flush()
    row = TariffConstructor(
        name=payload.name,
        description=payload.description,
        base_price=payload.base_price,
        plan_id=plan.id,
        remnawave_profile_id=payload.remnawave_profile_id,
        enabled=payload.enabled,
        sort_order=payload.sort_order,
    )
    db.add(row)
    await db.flush()
    options = []
    for item in payload.options:
        opt = TariffConstructorOption(constructor_id=row.id, **item.model_dump())
        db.add(opt)
        options.append(opt)
    await db.flush()
    _sync_plan(plan, row, options)
    await audit(db, "tariff.constructor.created", admin.email, str(row.id), {"name": row.name})
    await db.commit()
    await db.refresh(row)
    return _constructor_out(row, await _options(db, row.id))


@router.put("/api/admin/tariff-constructors/{constructor_id}")
async def admin_constructor_update(constructor_id: int, payload: ConstructorIn, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_plans"))):
    from .main import audit

    row = await db.get(TariffConstructor, constructor_id)
    if not row:
        raise HTTPException(404, "Not found")
    _validate_options(payload.options, payload.enabled)
    row.name = payload.name
    row.description = payload.description
    row.base_price = payload.base_price
    row.remnawave_profile_id = payload.remnawave_profile_id
    row.enabled = payload.enabled
    row.sort_order = payload.sort_order
    for old in await _options(db, row.id):
        await db.delete(old)
    await db.flush()
    options = []
    for item in payload.options:
        opt = TariffConstructorOption(constructor_id=row.id, **item.model_dump())
        db.add(opt)
        options.append(opt)
    await db.flush()
    plan = await db.get(Plan, row.plan_id) if row.plan_id else None
    if plan is None:
        plan = Plan(name=row.name, price=row.base_price, duration_days=30, enabled=row.enabled)
        db.add(plan)
        await db.flush()
        row.plan_id = plan.id
    _sync_plan(plan, row, options)
    await audit(db, "tariff.constructor.updated", admin.email, str(row.id))
    await db.commit()
    return _constructor_out(row, await _options(db, row.id))


@router.delete("/api/admin/tariff-constructors/{constructor_id}")
async def admin_constructor_delete(constructor_id: int, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_plans"))):
    from .main import audit

    row = await db.get(TariffConstructor, constructor_id)
    if not row:
        raise HTTPException(404, "Not found")
    row.enabled = False
    if row.plan_id:
        plan = await db.get(Plan, row.plan_id)
        if plan:
            plan.enabled = False
    await audit(db, "tariff.constructor.disabled", admin.email, str(row.id))
    await db.commit()
    return {"ok": True, "enabled": False}
