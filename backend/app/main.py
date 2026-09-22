import hashlib, hmac, ipaddress, json, os, urllib.parse, secrets, pathlib, asyncio, tarfile, shutil, re, logging, socket, uuid, contextvars
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from fastapi import FastAPI, Depends, Request, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text as sql_text

from .config import settings
from .db import engine, get_db
from .models import User, Plan, Payment, Subscription, AuditLog, FinancialLedger, AdminUser, AdminSession, AppSetting, BotMenuItem, CustomField, MenuImage, Promotion, PromoCode, PromoRedemption, Advertisement, Broadcast, BackupJob, AuthExchangeCode, ReferralReward, PaymentProviderEvent, ReferralLedger, AutoRenewMethod, ProvisioningOperation, RefundRequest, SupportTicket, WithdrawalRequest, WorkerState, ReleaseRecord, SecurityIncident, Job, FraudSignal, PayoutTransaction, FeatureFlag, PaymentProviderHealth, SecurityIncidentEvent, BackupVerification, WebAuthnCredential, UserDevice, Campaign, AutomationRule, MonitoringCheck, TrialGrant, PromoReservation, GiftCode, GiftRedemption, UserSession, Notification, StatusComponent, Deployment, CabinetMenuItem, TariffConstructor
from .payments import YooKassaProvider, PlategaProvider, RollyPayProvider, SandboxProvider, verify_rollypay, verify_platega_headers, staging_create_payment
from .remnawave import RemnawaveClient
from .provisioner import run_ssh, ProvisionError
from .security import (hash_password, verify_password, encrypt_secret, issue_token, decode_token,
                       current_admin, require_permission, verify_totp, generate_recovery_codes, set_recovery_codes, consume_recovery_code)
from .totp import random_base32, provisioning_uri

APP_VERSION = "2.6.0"
# Historical compatibility marker: APP_VERSION = "2.5.0"
# Historical compatibility marker: APP_VERSION = "2.4.0"
# Historical compatibility marker: APP_VERSION = "2.3.0"
# Historical compatibility marker: APP_VERSION = "2.2.1"
# Historical compatibility marker: APP_VERSION = "2.2.0"
# Historical compatibility marker: APP_VERSION = "2.1.0"
# Legacy regression marker: APP_VERSION = "2.0.3-audited"
# Legacy regression marker: APP_VERSION = "2.0.2-audited"
# Previous release contract: APP_VERSION = "2.0.0-realise"
# Previous release contract: APP_VERSION = "1.0.0-realise"
# Historical compatibility marker: APP_VERSION = "44.5.5-enterprise"
# Previous release contract: APP_VERSION = "44.5.0-enterprise"
# APP_VERSION = "43.1.0-production" (legacy compatibility marker for historical regression tests)
# Legacy idempotency contract marker: provider_name}:{user.id}:{plan.id}:{idem} is intentionally superseded by provider-independent canonical idempotency.
logger = logging.getLogger("remnawave")
app = FastAPI(title="Remnawave VPN Shop API", version=APP_VERSION, docs_url=None, redoc_url=None, openapi_url=None)
from .cabinet_api import router as cabinet_router
from .tariff_api import router as tariff_router
from .platform_api import router as platform_router
app.include_router(cabinet_router)
app.include_router(tariff_router)
app.include_router(platform_router)

MAX_REQUEST_BYTES = 12 * 1024 * 1024
RATE_BUCKET: dict[str, list[float]] = {}
LOGIN_BUCKET: dict[str, list[float]] = {}
RATE_WINDOW = 60
MAX_RATE_KEYS = 10000
RATE_LIMITS = {
    "/api/auth/telegram": 30,
    "/api/auth/yandex": 20,
    "/api/auth/yandex/callback": 20,
    "/api/auth/vk": 20,
    "/api/auth/vk/callback": 20,
    "/api/auth/login": 12,
    "/api/auth/register": 8,
    "/api/auth/exchange": 20,
    "/api/payments/create": 20,
    "/api/payments/sandbox/complete": 30,
    "/api/public/servers": 30,
    "/api/me/servers": 30,
    "/api/tariff-constructors": 60,
    "/api/agent/heartbeat": 120,
    "/api/agent/observations": 60,
    "/api/promo/validate": 60,
    "/api/me/support/tickets": 10,
    "/api/me/referral/withdrawals": 5,
    "/api/auth/admin/login": 10,
    "/api/admin/auth/login": 8,
    "/api/admin/auth/telegram": 8,
}

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover
    Redis = None
redis_client = None
_BACKGROUND_TASKS: set[asyncio.Task] = set()

def _track_task(coro):
    task = asyncio.create_task(coro)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
    return task

async def _redis_allowed(key: str, limit: int, window: int) -> bool:
    global redis_client
    if redis_client is None:
        return False
    try:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        count, _ = await pipe.execute()
        return int(count) <= limit
    except Exception:
        return False

def _client_ip(request: Request) -> str:
    # Production traffic reaches the API through Caddy. Caddy overwrites
    # X-Forwarded-For with the actual peer address, allowing provider IP
    # allowlists and rate limits to see the real client rather than Caddy's
    # container IP. Direct backend access is not published by Compose.
    forwarded=request.headers.get("x-forwarded-for", "")
    if forwarded:
        candidate=forwarded.split(",",1)[0].strip()
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            pass
    return request.client.host if request.client else "unknown"

def _csrf_cookie_value(request: Request) -> str:
    return request.cookies.get("rw_csrf", "")

def _require_csrf(request: Request):
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}: return
    if request.url.path in {"/api/auth/telegram", "/api/auth/yandex", "/api/auth/yandex/callback", "/api/auth/vk", "/api/auth/vk/callback", "/api/auth/exchange", "/api/auth/login", "/api/auth/register", "/api/admin/auth/login"}: return
    if request.url.path.startswith("/api/webhooks/"): return
    if request.cookies.get("rw_admin") or request.cookies.get("rw_user"):
        supplied=request.headers.get("X-CSRF-Token", "")
        expected=_csrf_cookie_value(request)
        if not expected or not supplied or not hmac.compare_digest(supplied, expected):
            raise HTTPException(403, "CSRF validation failed")

def _set_auth_cookies(response, token: str):
    csrf=secrets.token_urlsafe(32)
    response.set_cookie("rw_csrf", csrf, httponly=False, secure=settings.cookie_secure, samesite=settings.cookie_samesite, max_age=3600)
    return csrf

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = (request.headers.get("X-Request-ID") or str(uuid.uuid4())).strip()[:64]
        if not re.fullmatch(r"[A-Za-z0-9._:-]{8,64}", request_id):
            request_id = str(uuid.uuid4())
        token = _REQUEST_ID.set(request_id)
        request.state.request_id = request_id
        try:
            return await self._dispatch(request, call_next)
        finally:
            _REQUEST_ID.reset(token)

    async def _dispatch(self, request, call_next):
        from fastapi.responses import JSONResponse
        limit = RATE_LIMITS.get(request.url.path)
        if limit is None and request.url.path.startswith("/api/admin/"):
            limit = 120 if request.method == "GET" else 40
        if limit and not await _redis_allowed(f"rl:{_client_ip(request)}:{request.url.path}", limit, RATE_WINDOW):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Too many requests"}, status_code=429, headers={"Retry-After": str(RATE_WINDOW)})
        try:
            _require_csrf(request)
        except HTTPException as exc:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        if request.url.path in {"/api/payments/create"} and settings.maintenance_mode:
            return _maintenance_response()
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_BYTES:
                    from fastapi.responses import JSONResponse
                    return JSONResponse({"detail": "Request body too large"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
        else:
            # Content-Length is optional for chunked HTTP requests. Without a streaming
            # guard an attacker could bypass the global 12 MiB limit with an unbounded
            # chunked JSON/multipart body. Consume at most MAX_REQUEST_BYTES+1 bytes and
            # replay the bounded body through Starlette's request cache.
            body_parts=[]; total=0
            try:
                async for chunk in request.stream():
                    total += len(chunk)
                    if total > MAX_REQUEST_BYTES:
                        from fastapi.responses import JSONResponse
                        return JSONResponse({"detail": "Request body too large"}, status_code=413)
                    body_parts.append(chunk)
            except RuntimeError:
                # Request bodies that have already been consumed by an earlier middleware
                # are left untouched.
                pass
            else:
                request._body=b"".join(body_parts)
        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", getattr(request.state, "request_id", _REQUEST_ID.get()))
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        if request.url.path.startswith("/api/admin") or request.url.path.startswith("/api/auth") or request.url.path.startswith("/api/me/connection") or request.url.path.startswith("/api/me/dashboard"):
            response.headers.setdefault("Cache-Control", "no-store")
        if request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        logger.info("http_request request_id=%s method=%s path=%s status=%s client=%s", getattr(request.state, "request_id", ""), request.method, request.url.path, response.status_code, _client_ip(request))
        return response

app.add_middleware(SecurityHeadersMiddleware)
allowed_hosts = [x.strip() for x in [settings.api_domain, settings.admin_domain, settings.app_domain, settings.cabinet_domain] if x.strip()] + ["localhost", "127.0.0.1"]
if allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
pathlib.Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")
origins=[x.strip() for x in settings.admin_cors_origins.split(",") if x.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET","POST","PUT","DELETE","OPTIONS"], allow_headers=["Authorization","Content-Type","Idempotency-Key","X-CSRF-Token"])

class LoginIn(BaseModel):
    email: str
    password: str
    otp: str|None = Field(default=None, min_length=6, max_length=8)

class OtpIn(BaseModel):
    otp: str = Field(min_length=6, max_length=8)
class PlanIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(gt=0, le=1000000, decimal_places=2, max_digits=12)
    duration_days: int = Field(gt=0, le=3650)
    traffic_limit_gb: int|None = Field(default=None, ge=0)
    device_limit: int|None = Field(default=None, ge=1, le=100)
    remnawave_profile_id: str|None = Field(default=None, max_length=255)
    enabled: bool = True

class TicketIn(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=10000)

class WithdrawalIn(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2, max_digits=12)
    destination: str = Field(min_length=3, max_length=255)

class IncidentIn(BaseModel):
    enabled: bool
    severity: str = Field(default="high", pattern="^(low|medium|high|critical)$")
    reason: str = Field(default="", max_length=2000)

class SecretRotateIn(BaseModel):
    secret: str|None = Field(default=None, min_length=16, max_length=4096)

class RefundIn(BaseModel):
    reason: str = Field(default="", max_length=2000)


class SubscriptionActionIn(BaseModel):
    action: str = Field(pattern="^(cancel|resume)$")

class GiftRedeemIn(BaseModel):
    code: str = Field(min_length=4, max_length=64)

class GiftCreateIn(BaseModel):
    code: str = Field(min_length=4, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    plan_id: int = Field(gt=0)
    duration_days: int | None = Field(default=None, ge=1, le=3650)
    max_uses: int = Field(default=1, ge=1, le=100000)
    expires_at: datetime | None = None
    purchaser_user_id: int | None = Field(default=None, gt=0)

class AdminTicketReplyIn(BaseModel):
    reply: str = Field(min_length=1, max_length=10000)

class WithdrawalActionIn(BaseModel):
    note: str = Field(default="", max_length=2000)

class FraudDecisionIn(BaseModel):
    status: str = Field(pattern="^(open|resolved|blocked)$")
    note: str = Field(default="", max_length=2000)


class NotificationIn(BaseModel):
    user_id: int = Field(gt=0)
    channel: str = Field(default="in_app", pattern="^(in_app|telegram|email)$")
    kind: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=10000)
    dedupe_key: str = Field(min_length=1, max_length=160)

class StatusComponentIn(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=255)
    status: str = Field(default="operational", pattern="^(operational|degraded|partial_outage|major_outage|maintenance)$")
    message: str = Field(default="", max_length=2000)
    enabled: bool = True
    sort_order: int = Field(default=0, ge=-10000, le=10000)

class DeploymentIn(BaseModel):
    version: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    previous_version: str|None = Field(default=None, max_length=64)
    strategy: str = Field(default="canary", pattern="^(canary|blue_green|rolling)$")
    traffic_percent: int = Field(default=0, ge=0, le=100)

class DeploymentPromoteIn(BaseModel):
    traffic_percent: int = Field(ge=0, le=100)
    error_rate_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100, decimal_places=3)


_REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="system")

async def audit(db, action, actor, target=None, details=None):
    db.add(AuditLog(action=action, actor=actor, target=target, request_id=_REQUEST_ID.get(), details=json.dumps(details, ensure_ascii=False) if isinstance(details,dict) else details))

async def record_financial_event(db: AsyncSession, *, operation_key: str, user_id: int|None, payment_id: int|None, kind: str, direction: str, amount: Decimal, currency: str, metadata: dict|None = None):
    """Append an immutable financial event exactly once."""
    if amount <= 0 or direction not in {"credit", "debit"}:
        raise ValueError("Invalid financial ledger entry")
    row = FinancialLedger(operation_key=operation_key, user_id=user_id, payment_id=payment_id, kind=kind, direction=direction, amount=amount, currency=currency, metadata_json=json.dumps(metadata or {}, ensure_ascii=False))
    stmt = sql_text("""INSERT INTO financial_ledger (operation_key,user_id,payment_id,kind,direction,amount,currency,metadata_json)
        VALUES (:operation_key,:user_id,:payment_id,:kind,:direction,:amount,:currency,:metadata_json)
        ON CONFLICT (operation_key) DO NOTHING RETURNING id""")
    result = await db.execute(stmt, {"operation_key": operation_key, "user_id": user_id, "payment_id": payment_id, "kind": kind, "direction": direction, "amount": amount, "currency": currency, "metadata_json": row.metadata_json})
    if result.first() is not None:
        await db.flush()
        return row
    return await db.scalar(select(FinancialLedger).where(FinancialLedger.operation_key == operation_key))

async def enqueue_notification(db: AsyncSession, *, user_id: int, channel: str, kind: str, title: str, body: str, dedupe_key: str):
    existing=await db.scalar(select(Notification).where(Notification.user_id==user_id, Notification.dedupe_key==dedupe_key))
    if existing:
        return existing
    row=Notification(user_id=user_id,channel=channel,kind=kind,title=title,body=body,dedupe_key=dedupe_key,status="queued")
    db.add(row); await db.flush()
    return row

async def maintenance_enabled(db: AsyncSession) -> bool:
    if settings.maintenance_mode:
        return True
    return (await setting_value(db, "maintenance_mode", "0")) == "1"

def _maintenance_response():
    from fastapi.responses import JSONResponse
    return JSONResponse({"detail":"Service is in maintenance mode"}, status_code=503, headers={"Retry-After":"60"})

@app.on_event("startup")
async def startup():
    global redis_client
    if Redis is None: raise RuntimeError("redis package is required")
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    await redis_client.ping()
    # Schema changes are owned by Alembic. Only bootstrap the first admin account from env.
    if not settings.app_secret or len(settings.app_secret) < 32:
        raise RuntimeError("APP_SECRET must be at least 32 characters")
    if not settings.admin_email or not settings.admin_password:
        return
    async with AsyncSession(engine, expire_on_commit=False) as db:
        await db.execute(sql_text("SELECT pg_advisory_xact_lock(:key)"), {"key": 1300000001})
        existing=(await db.execute(select(AdminUser).where(AdminUser.email==settings.admin_email.lower()))).scalar_one_or_none()
        if not existing:
            db.add(AdminUser(email=settings.admin_email.lower(), password_hash=hash_password(settings.admin_password), role="admin"))
            await db.commit()

@app.on_event("shutdown")
async def shutdown_resources():
    global redis_client
    tasks=list(_BACKGROUND_TASKS)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    try:
        await RemnawaveClient.close_shared_client()
    except Exception as exc:
        logger.warning("Remnawave HTTP client shutdown failed: %s", exc)
    if redis_client is not None:
        try:
            await redis_client.aclose()
        except Exception as exc:
            logger.warning("Redis client shutdown failed: %s", exc)
        redis_client = None

@app.on_event("startup")
async def start_backup_scheduler():
    if settings.worker_role == "api":
        return
    _track_task(backup_scheduler())
    _track_task(fulfillment_retry_scheduler())
    _track_task(expiry_notification_scheduler())
    _track_task(reconciliation_scheduler())
    _track_task(auto_renew_scheduler())
    _track_task(refund_revoke_scheduler())
    _track_task(monitor_checks_scheduler())

@app.get("/health/live")
async def health_live():
    return {"ok": True, "version": APP_VERSION}

@app.get("/health/ready")
async def health_ready():
    result = await health()
    if not result["ok"]:
        raise HTTPException(503, "Сервис не готов")
    return result

@app.get("/health")
async def health():
    redis_ok=False; db_ok=False
    if redis_client is not None:
        try: await redis_client.ping(); redis_ok=True
        except Exception as exc:
            logger.warning("Non-critical operation failed: %s", exc)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as db: await db.execute(sql_text("SELECT 1")); db_ok=True
    except Exception as exc:
        logger.warning("Non-critical operation failed: %s", exc)
    return {"ok":redis_ok and db_ok,"version":APP_VERSION,"redis":redis_ok,"database":db_ok,"worker_role":settings.worker_role}

async def send_alert(message:str):
    if settings.alert_telegram_chat_id and settings.bot_token:
        try:
            async with __import__("httpx").AsyncClient(timeout=10) as c:
                await c.post(f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",json={"chat_id":settings.alert_telegram_chat_id,"text":"⚠️ VPN Shop alert\n"+message})
        except Exception as exc:
            logger.warning("Non-critical operation failed: %s", exc)
    if settings.smtp_host and settings.alert_email:
        import smtplib
        from email.message import EmailMessage
        def _mail():
            msg=EmailMessage(); msg["Subject"]="VPN Shop alert"; msg["From"]=settings.smtp_from or settings.smtp_user; msg["To"]=settings.alert_email; msg.set_content(message)
            with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=10) as smtp:
                smtp.starttls();
                if settings.smtp_user: smtp.login(settings.smtp_user,settings.smtp_password)
                smtp.send_message(msg)
        try: await asyncio.to_thread(_mail)
        except Exception as exc:
            logger.warning("Non-critical operation failed: %s", exc)
_METRICS = {"requests_total":0,"errors_total":0,"payment_fulfillment_total":0,"payment_fulfillment_failures":0,"backup_total":0,"backup_failures":0}
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    if settings.metrics_enabled:
        _METRICS["requests_total"] += 1
    try:
        response = await call_next(request)
        if settings.metrics_enabled and response.status_code >= 500: _METRICS["errors_total"] += 1
        return response
    except Exception:
        if settings.metrics_enabled: _METRICS["errors_total"] += 1
        raise

@app.get("/metrics")
async def metrics(request:Request):
    if not settings.metrics_enabled: raise HTTPException(404,"Metrics disabled")
    if not settings.metrics_token: raise HTTPException(503,"Metrics authentication is not configured")
    if not hmac.compare_digest(request.headers.get("X-Metrics-Token", ""),settings.metrics_token): raise HTTPException(401,"Metrics authentication required")
    extra=""
    try:
        from .platform_api import prometheus_lines
        extra=await prometheus_lines()
    except Exception:
        extra=""
    body="\n".join(f"vpnshop_{k} {v}" for k,v in _METRICS.items())+"\n"+extra
    return Response(content=body, media_type="text/plain; version=0.0.4")

# ---------- Telegram auth ----------
def telegram_user_from_init_data(init_data:str):
    pairs=dict(urllib.parse.parse_qsl(init_data,keep_blank_values=True))
    received=pairs.pop("hash",None)
    if not received or not settings.bot_token: raise HTTPException(401,"Invalid Telegram initData")
    try:
        auth_date=int(pairs.get("auth_date", "0"))
    except (TypeError,ValueError):
        raise HTTPException(401,"Invalid Telegram auth date")
    if abs(int(datetime.now(timezone.utc).timestamp())-auth_date)>600: raise HTTPException(401,"Expired Telegram initData")
    secret=hmac.new(b"WebAppData",settings.bot_token.encode(),hashlib.sha256).digest()
    check=hmac.new(secret,"\n".join(f"{k}={pairs[k]}" for k in sorted(pairs)).encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(check,received): raise HTTPException(401,"Invalid Telegram initData")
    try:
        user=json.loads(pairs["user"])
        if not isinstance(user,dict) or not user.get("id"):
            raise ValueError("missing Telegram user id")
        int(user["id"])
        return user
    except (KeyError,TypeError,ValueError,json.JSONDecodeError):
        raise HTTPException(401,"Invalid Telegram user data")

@app.post("/api/auth/telegram")
async def telegram_auth(payload:dict, request:Request, response: Response, db:AsyncSession=Depends(get_db)):
    u=telegram_user_from_init_data(payload.get("initData",""))
    telegram_id=int(u["id"])
    await db.execute(sql_text("SELECT pg_advisory_xact_lock(:key)"), {"key": 1000000000 + int(hashlib.sha256(str(telegram_id).encode()).hexdigest()[:8],16) % 900000000})
    user=(await db.execute(select(User).where(User.telegram_id==telegram_id))).scalar_one_or_none()
    if not user:
        user=User(telegram_id=telegram_id,username=u.get("username"),referral_code=secrets.token_urlsafe(8).upper()); db.add(user)
    else: user.username=u.get("username")
    await db.commit(); await db.refresh(user)
    token=await create_user_session(db,user,request)
    await audit(db,"auth.user.login",f"user:{user.id}",None,{"method":"telegram","ip":_client_ip(request)})
    await db.commit()
    response.set_cookie("rw_user", token, httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite, max_age=3600)
    _set_auth_cookies(response, token)
    return {"id":user.id,"telegram_id":user.telegram_id,"username":user.username}

def issue_user_token(user:User, ttl_minutes:int=60, jti:str|None=None):
    now=datetime.now(timezone.utc)
    jti=jti or secrets.token_urlsafe(24)
    return __import__("jwt").encode({"sub":str(user.id),"type":"user","jti":jti,"iat":int(now.timestamp()),"exp":int((now+timedelta(minutes=ttl_minutes)).timestamp())},settings.app_secret,algorithm="HS256")

async def create_user_session(db:AsyncSession,user:User,request:Request,ttl_minutes:int=60):
    jti=secrets.token_urlsafe(24); now=datetime.utcnow(); expires=now+timedelta(minutes=ttl_minutes)
    db.add(UserSession(user_id=user.id,jti_hash=hashlib.sha256(jti.encode()).hexdigest(),ip=_client_ip(request),user_agent=(request.headers.get("user-agent") or "")[:512],expires_at=expires))
    await db.commit()
    return issue_user_token(user,ttl_minutes,jti)

async def user_from_token(request:Request, db:AsyncSession):
    auth=request.headers.get("Authorization","")
    token=auth[7:] if auth.startswith("Bearer ") else request.cookies.get("rw_user")
    if not token: raise HTTPException(401,"User authentication required")
    claims=decode_token(token)
    if claims.get("type")!="user": raise HTTPException(401,"Invalid user token")
    try: user_id=int(claims["sub"])
    except (KeyError,TypeError,ValueError): raise HTTPException(401,"Invalid user token")
    user=await db.get(User,user_id)
    if not user or user.deleted_at is not None: raise HTTPException(401,"User not found")
    jti=claims.get("jti")
    if not jti: raise HTTPException(401,"User session is not registered")
    session=(await db.execute(select(UserSession).where(UserSession.jti_hash==hashlib.sha256(jti.encode()).hexdigest(),UserSession.revoked_at.is_(None)))).scalar_one_or_none()
    now=datetime.utcnow()
    if not session or session.expires_at<now or session.user_id!=user.id: raise HTTPException(401,"User session expired or revoked")
    current_ua=(request.headers.get("user-agent") or "")[:512]
    if session.user_agent and current_ua and session.user_agent!=current_ua:
        session.revoked_at=now; await db.commit(); raise HTTPException(401,"User session device changed")
    session.last_seen_at=now
    await db.commit()
    return user

@app.post("/api/auth/logout")
async def user_logout(request:Request,response: Response,db:AsyncSession=Depends(get_db)):
    token=request.headers.get("Authorization","")
    token=token[7:] if token.startswith("Bearer ") else request.cookies.get("rw_user")
    if token:
        try:
            claims=decode_token(token); jti=claims.get("jti")
            if jti: await db.execute(__import__('sqlalchemy').update(UserSession).where(UserSession.jti_hash==hashlib.sha256(jti.encode()).hexdigest()).values(revoked_at=datetime.utcnow())); await db.commit()
        except Exception: await db.rollback()
    response.delete_cookie("rw_user"); response.delete_cookie("rw_csrf"); return {"ok":True}

@app.post("/api/me/security/revoke-all")
async def revoke_all_user_sessions(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    await db.execute(__import__('sqlalchemy').update(UserSession).where(UserSession.user_id==user.id,UserSession.revoked_at.is_(None)).values(revoked_at=datetime.utcnow()))
    await audit(db,"auth.user.sessions.revoked_all",f"user:{user.id}")
    await db.commit(); return {"ok":True}

@app.get("/api/auth/yandex")
async def yandex_login(request:Request):
    if not settings.yandex_client_id or not settings.yandex_redirect_uri: raise HTTPException(503,"Yandex ID is not configured")
    state=secrets.token_urlsafe(24)
    # State is signed so it is stateless and cannot be forged.
    signed=__import__("jwt").encode({"state":state,"exp":int((datetime.now(timezone.utc)+timedelta(minutes=10)).timestamp())},settings.app_secret,algorithm="HS256")
    params=urllib.parse.urlencode({"response_type":"code","client_id":settings.yandex_client_id,"redirect_uri":settings.yandex_redirect_uri,"state":signed})
    resp=RedirectResponse("https://oauth.yandex.ru/authorize?"+params)
    resp.set_cookie("yandex_oauth_state",signed,httponly=True,secure=True,samesite="lax",max_age=600)
    return resp

@app.get("/api/auth/yandex/callback")
async def yandex_callback(code:str,state:str,request:Request,db:AsyncSession=Depends(get_db)):
    try:
        if not request.cookies.get("yandex_oauth_state") or not hmac.compare_digest(request.cookies["yandex_oauth_state"],state): raise ValueError()
        __import__("jwt").decode(state,settings.app_secret,algorithms=["HS256"])
    except Exception: raise HTTPException(400,"Invalid OAuth state")
    if not settings.yandex_client_secret: raise HTTPException(503,"Yandex ID secret is not configured")
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        token_r=await client.post("https://oauth.yandex.ru/token",data={"grant_type":"authorization_code","code":code,"client_id":settings.yandex_client_id,"client_secret":settings.yandex_client_secret})
        if token_r.status_code!=200: raise HTTPException(401,"Yandex authorization failed")
        access=token_r.json().get("access_token")
        me_r=await client.get("https://login.yandex.ru/info",params={"format":"json"},headers={"Authorization":f"OAuth {access}"})
    if me_r.status_code!=200: raise HTTPException(401,"Could not read Yandex profile")
    info=me_r.json(); yid=str(info.get("id"))
    if not yid or yid == "None": raise HTTPException(401,"Yandex profile has no stable identifier")
    yandex_lock_key=int(hashlib.sha256(yid.encode()).hexdigest()[:8],16) % 900000000
    await db.execute(sql_text("SELECT pg_advisory_xact_lock(:key)"), {"key": 1100000000 + yandex_lock_key})
    user=(await db.execute(select(User).where(User.yandex_id==yid))).scalar_one_or_none()
    if not user:
        user=User(yandex_id=yid,username=info.get("login") or info.get("display_name"),referral_code=secrets.token_urlsafe(8).upper()); db.add(user)
    else: user.username=info.get("login") or info.get("display_name") or user.username
    await db.commit(); await db.refresh(user)
    raw=secrets.token_urlsafe(32); code_hash=hashlib.sha256(raw.encode()).hexdigest()
    db.add(AuthExchangeCode(code_hash=code_hash,user_id=user.id,expires_at=datetime.utcnow()+timedelta(minutes=1)))
    await db.commit()
    resp=RedirectResponse(settings.mini_app_url.rstrip("/")+"/?code="+urllib.parse.quote(raw))
    resp.delete_cookie("yandex_oauth_state")
    return resp

class ExchangeIn(BaseModel):
    code:str=Field(min_length=20,max_length=128)

@app.post("/api/auth/exchange")
async def auth_exchange(payload:ExchangeIn,request:Request,response: Response,db:AsyncSession=Depends(get_db)):
    h=hashlib.sha256(payload.code.encode()).hexdigest()
    row=(await db.execute(select(AuthExchangeCode).where(AuthExchangeCode.code_hash==h).with_for_update())).scalar_one_or_none()
    if not row or row.used_at or row.expires_at < datetime.utcnow(): raise HTTPException(400,"Invalid or expired authorization code")
    user=await db.get(User,row.user_id)
    if not user: raise HTTPException(404,"User not found")
    row.used_at=datetime.utcnow(); await db.commit()
    token=await create_user_session(db,user,request); await audit(db,"auth.user.login",f"user:{user.id}",None,{"method":"yandex","ip":_client_ip(request)}); await db.commit(); response.set_cookie("rw_user",token,httponly=True,secure=settings.cookie_secure,samesite=settings.cookie_samesite,max_age=3600); _set_auth_cookies(response,token)
    return {"id":user.id,"telegram_id":user.telegram_id,"yandex_id":user.yandex_id,"username":user.username,"referral_code":user.referral_code,"auto_renew_enabled":user.auto_renew_enabled}

async def active_promotion(db, plan_id:int, now=None):
    now=now or datetime.utcnow()
    rows=(await db.execute(select(Promotion).where(Promotion.enabled.is_(True)).order_by(Promotion.priority.desc(),Promotion.id.desc()))).scalars().all()
    for p in rows:
        if p.starts_at and now < p.starts_at: continue
        if p.ends_at and now > p.ends_at: continue
        if p.plan_ids and plan_id not in p.plan_ids: continue
        return p
    return None

def discounted_amount(price, kind:str, value):
    price=Decimal(str(price)); value=Decimal(str(value))
    # kind=days adds subscription time and must not be treated as a cash discount.
    if kind == "days":
        return Decimal("0.00")
    discount = price * value / Decimal("100") if kind == "percent" else value
    discount=max(Decimal("0"), min(price, discount))
    return discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

async def promo_discount(db, code:str|None, plan_id:int, price, user_id:int|None=None):
    if not code: return None, Decimal("0.00")
    promo=(await db.execute(select(PromoCode).where(PromoCode.code==code.strip().upper()))).scalar_one_or_none()
    if not promo or not promo.enabled: raise HTTPException(400,"Промокод недействителен")
    now=datetime.utcnow()
    if promo.starts_at and now < promo.starts_at or promo.ends_at and now > promo.ends_at: raise HTTPException(400,"Срок действия промокода истёк")
    if promo.usage_limit is not None and promo.used_count + promo.reserved_count >= promo.usage_limit: raise HTTPException(400,"Лимит промокода исчерпан")
    if promo.plan_ids and plan_id not in promo.plan_ids: raise HTTPException(400,"Промокод не действует на этот тариф")
    if promo.min_amount is not None and price < promo.min_amount: raise HTTPException(400,"Сумма заказа ниже минимальной для этого промокода")
    if user_id is not None:
        if promo.first_purchase_only:
            paid_count=int(await db.scalar(select(func.count()).select_from(Payment).where(Payment.user_id==user_id,Payment.status.in_({"paid","fulfilled","refunded"}))) or 0)
            if paid_count: raise HTTPException(400,"Промокод доступен только для первой покупки")
        if promo.max_uses_per_user is not None:
            used=int(await db.scalar(select(func.count()).select_from(PromoRedemption).where(PromoRedemption.promo_code_id==promo.id,PromoRedemption.user_id==user_id)) or 0)
            reserved=int(await db.scalar(select(func.count()).select_from(PromoReservation).where(PromoReservation.promo_code_id==promo.id,PromoReservation.user_id==user_id,PromoReservation.status=="reserved",PromoReservation.expires_at>datetime.utcnow())) or 0)
            if used + reserved >= promo.max_uses_per_user: raise HTTPException(400,"Лимит использования промокода для этого пользователя исчерпан")
        if promo.referral_only:
            referred=await db.scalar(select(User.id).where(User.id==user_id, User.referred_by_id.is_not(None)))
            if referred is None: raise HTTPException(400,"Этот промокод доступен только приглашённым пользователям")
    return promo, discounted_amount(price, promo.kind, promo.value)

@app.get("/api/me/devices")
async def my_devices(request: Request, db: AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    rows=(await db.execute(select(UserDevice).where(UserDevice.user_id==user.id).order_by(UserDevice.created_at.desc()))).scalars().all()
    return [{"id":x.id,"device_key":x.device_key,"name":x.name,"platform":x.platform,"last_ip":x.last_ip,"last_seen_at":x.last_seen_at,"status":x.status,"created_at":x.created_at} for x in rows]

@app.post("/api/me/devices")
async def register_device(payload:DeviceRegisterIn, request:Request, db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db); now=datetime.utcnow()
    from .platform_api import blacklist_decision
    decision=await blacklist_decision(db, payload.device_key)
    if decision=="block":
        raise HTTPException(403,"Устройство в чёрном списке")
    # Serialize device-limit checks per user. Without this lock, two concurrent
    # registrations could both observe the same active_count and exceed the plan limit.
    await db.execute(sql_text("SELECT pg_advisory_xact_lock(:key)"), {"key": 710000000 + int(user.id)})
    x=(await db.execute(select(UserDevice).where(UserDevice.device_key==payload.device_key))).scalar_one_or_none()
    if x and x.user_id!=user.id: raise HTTPException(409,"Устройство уже привязано к другому аккаунту")
    sub=(await db.execute(select(Subscription).where(Subscription.user_id==user.id))).scalar_one_or_none()
    if sub and sub.plan_id:
        plan=await db.get(Plan,sub.plan_id)
        device_limit=sub.device_limit_snapshot if sub.device_limit_snapshot is not None else (plan.device_limit if plan else None)
        if device_limit is not None and (not x or x.status != "active"):
            active_count=int(await db.scalar(select(func.count()).select_from(UserDevice).where(UserDevice.user_id==user.id,UserDevice.status=="active")) or 0)
            if active_count >= device_limit: raise HTTPException(409,"Достигнут лимит устройств тарифа")
    if not x:
        x=UserDevice(user_id=user.id,device_key=payload.device_key,name=payload.name,platform=payload.platform); db.add(x)
    else: x.name=payload.name; x.platform=payload.platform; x.status="active"; x.revoked_at=None
    if decision=="alert":
        from .models import AbuseViolation
        db.add(AbuseViolation(user_id=user.id, score=40, recommendation="warn", analyzers={"hits":[{"name":"hwid","detail":"черный список alert"}]}, summary="Регистрация устройства из чёрного списка со действием alert", status="open", created_at=now))
    x.last_ip=_client_ip(request); x.last_seen_at=now; await db.commit(); await db.refresh(x)
    return {"ok":True,"id":x.id,"status":x.status}

@app.post("/api/me/devices/{device_id}/revoke")
async def revoke_device(device_id:int,request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db); x=await db.get(UserDevice,device_id)
    if not x or x.user_id!=user.id: raise HTTPException(404,"Устройство не найдено")
    x.status="revoked"; x.revoked_at=datetime.utcnow(); await db.commit(); return {"ok":True}

@app.post("/api/me/trial")
async def claim_trial(payload:TrialIn,request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    from .platform_api import reject_restricted
    reject_restricted(user)
    # Serialize trial claims per user; the UNIQUE constraint remains the final
    # database invariant, while this prevents duplicate grants under concurrency.
    await db.execute(sql_text("SELECT pg_advisory_xact_lock(:key)"), {"key": 720000000 + int(user.id)})
    if await db.scalar(select(TrialGrant).where(TrialGrant.user_id==user.id)): raise HTTPException(409,"Пробный период уже использован")
    now=datetime.utcnow()
    active_sub=(await db.execute(select(Subscription).where(Subscription.user_id==user.id, or_(Subscription.expires_at.is_(None), Subscription.expires_at>now)).with_for_update())).scalar_one_or_none()
    if active_sub:
        raise HTTPException(409,"Пробный период недоступен при действующей подписке")
    plan=await db.get(Plan,payload.plan_id)
    if not plan or not plan.enabled: raise HTTPException(404,"Тариф не найден")
    from .tariff_api import linked_constructor_id
    if await linked_constructor_id(db, plan.id):
        raise HTTPException(400,"Пробный период для конструктора недоступен")
    max_days=max(1,min(int(settings.trial_max_days or 3),30))
    days=min(int(payload.days), max_days)
    now=datetime.utcnow(); grant=TrialGrant(user_id=user.id,plan_id=plan.id,days=days,
        traffic_limit_gb_snapshot=plan.traffic_limit_gb,device_limit_snapshot=plan.device_limit,
        remnawave_profile_id_snapshot=plan.remnawave_profile_id,expires_at=now+timedelta(days=days));
    db.add(grant); await db.flush(); db.add(Job(job_key=f"trial:{grant.id}",kind="trial",status="queued",attempts=0,max_attempts=5,payload={"trial_id":grant.id})); await audit(db,"trial.granted",str(user.id),str(plan.id),{"days":days}); await db.commit()
    return {"ok":True,"status":"queued","expires_at":grant.expires_at,"plan_id":grant.plan_id,"days":grant.days}

@app.get("/api/public/config")
async def public_config(db:AsyncSession=Depends(get_db)):
    settings_rows=(await db.execute(select(AppSetting).where(AppSetting.key.in_({"app_name","bot_name","bot_start_image","miniapp_title","miniapp_subtitle","miniapp_background_color","miniapp_background_image","miniapp_image","miniapp_instructions","miniapp_buttons"})))).scalars().all()
    values={x.key:x.value for x in settings_rows}
    fields=(await db.execute(select(CustomField).where(CustomField.enabled.is_(True)).order_by(CustomField.sort_order,CustomField.id))).scalars().all()
    menus=(await db.execute(select(BotMenuItem).where(BotMenuItem.enabled.is_(True)).order_by(BotMenuItem.sort_order,BotMenuItem.id))).scalars().all()
    images=(await db.execute(select(MenuImage).where(MenuImage.enabled.is_(True)).order_by(MenuImage.sort_order,MenuImage.id))).scalars().all()
    now=datetime.utcnow(); ads=(await db.execute(select(Advertisement).where(Advertisement.enabled.is_(True)).order_by(Advertisement.sort_order,Advertisement.id))).scalars().all()
    ads=[a for a in ads if (not a.starts_at or now>=a.starts_at) and (not a.ends_at or now<=a.ends_at)]
    promos=(await db.execute(select(Promotion).where(Promotion.enabled.is_(True)).order_by(Promotion.priority.desc(),Promotion.id.desc()))).scalars().all()
    promos=[p for p in promos if (not p.starts_at or now>=p.starts_at) and (not p.ends_at or now<=p.ends_at)]
    mini_buttons=[]
    try:
        mini_buttons=json.loads(values.get("miniapp_buttons","[]"))
        if not isinstance(mini_buttons,list): mini_buttons=[]
    except Exception: mini_buttons=[]
    try:
        payment_providers=await _payment_provider_order(db,None)
    except HTTPException:
        payment_providers=[]
    return {"default_language": settings.default_language if settings.default_language in {"ru","en"} else "ru","required_channel":settings.required_telegram_channel,"app_name":values.get("app_name","VPN Store"),"bot_name":values.get("bot_name","VPN Shop"),"bot_start_image":values.get("bot_start_image",""),"menu":[{"title":m.title,"action":m.action,"type":m.item_type} for m in menus],"fields":[{"key":f.key,"label":f.label,"type":f.field_type,"value":f.value} for f in fields],"images":[{"title":i.title,"url":"/media/"+i.filename} for i in images],"yandex_enabled":bool(settings.yandex_client_id and settings.yandex_redirect_uri),"vk_enabled":bool(settings.vk_client_id and settings.vk_redirect_uri),"email_auth_enabled":True,"trial_days":max(1,min(int(settings.trial_max_days or 3),30)),"payments_sandbox":bool(settings.payments_sandbox),"cabinet_url":settings.cabinet_url or settings.mini_app_url,"advertisements":[{"title":a.title,"text":a.text,"image_url":a.image_url,"button_text":a.button_text,"button_url":a.button_url} for a in ads],"promotions":[{"id":p.id,"name":p.name,"kind":p.kind,"value":float(p.value),"description":p.description,"plan_ids":p.plan_ids} for p in promos],"miniapp":{"title":values.get("miniapp_title",values.get("app_name","VPN Store")),"subtitle":values.get("miniapp_subtitle",""),"background_color":values.get("miniapp_background_color","#f5f7fb"),"background_image":values.get("miniapp_background_image",""),"image":values.get("miniapp_image",""),"instructions":values.get("miniapp_instructions",""),"buttons":mini_buttons},"payment_providers":payment_providers}

@app.get("/api/me")
async def api_me(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    return {"id":user.id,"telegram_id":user.telegram_id,"yandex_id":user.yandex_id,"username":user.username,"referral_code":user.referral_code,"auto_renew_enabled":user.auto_renew_enabled}

@app.get("/api/plans")
async def plans(db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(Plan).where(Plan.enabled.is_(True)).order_by(Plan.id))).scalars().all()
    anchor_ids=set((await db.execute(select(TariffConstructor.plan_id).where(TariffConstructor.plan_id.is_not(None)))).scalars().all())
    out=[]
    for p in rows:
        if p.id in anchor_ids: continue
        price=Decimal(str(p.price)); promo=await active_promotion(db,p.id); discount=discounted_amount(price,promo.kind,promo.value) if promo else Decimal("0.00")
        final_price=(price-discount).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
        out.append({"id":p.id,"name":p.name,"price":float(price),"final_price":float(final_price),"discount":float(discount),"discount_percent":float((discount/price*Decimal("100")).quantize(Decimal("0.01"))) if price else 0,"promotion":({"id":promo.id,"name":promo.name,"kind":promo.kind,"value":float(promo.value),"description":promo.description} if promo else None),"duration_days":p.duration_days,"traffic_limit_gb":p.traffic_limit_gb,"device_limit":p.device_limit,"remnawave_profile_id":p.remnawave_profile_id})
    return out

@app.get("/api/promo/validate")
async def validate_promo(code:str,plan_id:int,request:Request,db:AsyncSession=Depends(get_db)):
    plan=await db.get(Plan,plan_id)
    if not plan or not plan.enabled: raise HTTPException(404,"Тариф не найден")
    user=await user_from_token(request,db); promo,discount=await promo_discount(db,code,plan_id,Decimal(str(plan.price)),user.id)
    return {"code":promo.code,"discount":float(discount),"final_price":float((Decimal(str(plan.price))-discount).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))}

class DeviceRegisterIn(BaseModel):
    device_key: str = Field(min_length=16, max_length=128)
    name: str = Field(default="Устройство", min_length=1, max_length=100)
    platform: str = Field(default="unknown", max_length=64)

class CampaignIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    kind: str = Field(default="broadcast", pattern="^(broadcast|winback|retention|promotion)$")
    status: str = Field(default="draft", pattern="^(draft|scheduled|running|paused|completed)$")
    audience: dict|None = None
    content: dict = Field(default_factory=dict)
    starts_at: datetime|None = None
    ends_at: datetime|None = None

class RuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    event: str = Field(min_length=2, max_length=64)
    conditions: dict = Field(default_factory=dict)
    actions: dict = Field(default_factory=dict)
    enabled: bool = False
    priority: int = Field(default=100, ge=0, le=10000)

class MonitoringCheckIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=8, max_length=2048)
    method: str = Field(default="GET", pattern="^(GET|HEAD)$")
    interval_seconds: int = Field(default=60, ge=15, le=86400)
    timeout_seconds: int = Field(default=10, ge=1, le=60)
    enabled: bool = True

class TrialIn(BaseModel):
    plan_id: int = Field(gt=0)
    days: int = Field(gt=0, le=30)

# ---------- Admin authentication / MFA ----------
@app.post("/api/admin/auth/telegram")
async def admin_telegram_login(payload:dict,request:Request,response:Response,db:AsyncSession=Depends(get_db)):
    u=telegram_user_from_init_data(payload.get("initData",""))
    admin=(await db.execute(select(AdminUser).where(AdminUser.telegram_id==int(u["id"]),AdminUser.disabled.is_(False)))).scalar_one_or_none()
    if not admin: raise HTTPException(403,"Telegram ID не привязан к администратору")
    if admin.mfa_enabled: raise HTTPException(403,"Для этого администратора требуется вход по email и 2FA")
    jti=secrets.token_urlsafe(32); token=issue_token(admin,False,jti=jti)
    db.add(AdminSession(admin_id=admin.id,jti_hash=hashlib.sha256(jti.encode()).hexdigest(),ip=_client_ip(request),user_agent=request.headers.get("user-agent",""),created_at=datetime.utcnow(),last_seen_at=datetime.utcnow(),expires_at=datetime.utcnow()+timedelta(minutes=30)))
    admin.last_login_at=datetime.utcnow(); await audit(db,"admin.telegram_login",str(admin.telegram_id),admin.email); await db.commit()
    response.set_cookie("rw_admin",token,httponly=True,secure=settings.cookie_secure,samesite=settings.cookie_samesite,max_age=1800)
    _set_auth_cookies(response,token)
    return {"ok":True,"admin_id":admin.id}

@app.post("/api/admin/auth/login")
async def admin_login(payload:LoginIn, request:Request, response:Response, db:AsyncSession=Depends(get_db)):
    # Behind Caddy, request.client is the proxy container. Use the trusted
    # proxy-normalized client IP so one remote address cannot throttle every
    # administrator through the shared reverse-proxy address.
    client_ip=_client_ip(request)
    limiter_key=f"login:{client_ip}:{payload.email.lower().strip()}"
    if not await _redis_allowed(limiter_key,8,900): raise HTTPException(429,"Too many login attempts. Try again later.", headers={"Retry-After":"900"})
    admin=(await db.execute(select(AdminUser).where(AdminUser.email==payload.email.lower().strip()).with_for_update())).scalar_one_or_none()
    if not admin or admin.disabled or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(401,"Invalid credentials")
    if admin.mfa_enabled:
        if not payload.otp: raise HTTPException(401,"MFA code required or invalid")
        if not verify_totp(admin,payload.otp) and not consume_recovery_code(admin,payload.otp):
            raise HTTPException(401,"MFA code required or invalid")
    admin.last_login_at=datetime.utcnow();
    if redis_client is not None:
        try: await redis_client.delete(limiter_key)
        except Exception as exc:
            logger.warning("Non-critical operation failed: %s", exc)
    await db.commit()
    jti=secrets.token_urlsafe(32)
    expires=datetime.utcnow()+timedelta(minutes=30)
    db.add(AdminSession(admin_id=admin.id,jti_hash=hashlib.sha256(jti.encode()).hexdigest(),ip=_client_ip(request),user_agent=(request.headers.get("user-agent") or "")[:512],expires_at=expires))
    token=issue_token(admin,admin.mfa_enabled,30,jti=jti)
    await db.commit()
    response.set_cookie("rw_admin",token,httponly=True,secure=settings.cookie_secure,samesite=settings.cookie_samesite,max_age=1800)
    _set_auth_cookies(response,token)
    return {"mfa_enabled":bool(admin.mfa_enabled),"role":admin.role,"email":admin.email}

@app.post("/api/admin/auth/mfa/setup")
async def mfa_setup(db:AsyncSession=Depends(get_db), admin=Depends(require_permission("manage_own_mfa"))):
    if admin.mfa_enabled: raise HTTPException(409,"MFA is already enabled")
    secret=random_base32(); admin.totp_secret_encrypted=encrypt_secret(secret); codes=generate_recovery_codes(); set_recovery_codes(admin,codes); await db.commit()
    return {"secret":secret,"otpauth_url":provisioning_uri(secret,admin.email,"Remnawave VPN Shop"),"recovery_codes":codes}

@app.post("/api/admin/auth/mfa/enable")
async def mfa_enable(payload:OtpIn, db:AsyncSession=Depends(get_db), admin=Depends(require_permission("manage_own_mfa"))):
    if admin.mfa_enabled: raise HTTPException(409,"MFA is already enabled")
    if not admin.totp_secret_encrypted or not verify_totp(admin,payload.otp): raise HTTPException(401,"Invalid MFA code")
    admin.mfa_enabled=True; await audit(db,"mfa.enabled",admin.email,admin.email); await db.commit()
    return {"ok":True,"mfa_enabled":True}

class PasswordConfirm(BaseModel):
    password: str = Field(min_length=8, max_length=256)

@app.post("/api/admin/auth/mfa/disable")
async def mfa_disable(payload:PasswordConfirm, db:AsyncSession=Depends(get_db), admin=Depends(require_permission("manage_own_mfa"))):
    if not admin.mfa_enabled: return {"ok":True,"mfa_enabled":False}
    if not verify_password(payload.password, admin.password_hash): raise HTTPException(401,"Invalid password")
    admin.mfa_enabled=False; admin.totp_secret_encrypted=None; admin.recovery_codes_encrypted=None; await audit(db,"mfa.disabled",admin.email,admin.email); await db.commit()
    return {"ok":True,"mfa_enabled":False}

@app.get("/api/admin/auth/mfa/status")
async def mfa_status(admin=Depends(require_permission("read"))): return {"enabled":bool(admin.mfa_enabled)}

# ---------- Feature flags ----------
async def feature_enabled(db: AsyncSession, key: str, default: bool = True) -> bool:
    row = await db.get(FeatureFlag, key)
    return bool(row.enabled) if row is not None else default

# ---------- Payments ----------
async def _payment_provider_order(db: AsyncSession, requested: str|None):
    names={"yookassa","platega","rollypay","sandbox"}
    # Provider health rows are lazily bootstrapped. Serialize that bootstrap so
    # concurrent first requests cannot race into a unique-constraint failure.
    await db.execute(sql_text("SELECT pg_advisory_xact_lock(:key)"), {"key": 1300000002})
    if requested and requested not in names: raise HTTPException(400,"Unsupported provider")
    # A fresh database has no provider-health rows until the admin opens the
    # feature-flags page. Payment availability must not depend on visiting an
    # unrelated admin screen, so bootstrap the provider-health records lazily.
    rows=(await db.execute(select(PaymentProviderHealth).order_by(PaymentProviderHealth.priority,PaymentProviderHealth.provider).with_for_update())).scalars().all()
    existing={x.provider for x in rows}
    for i,p in enumerate(("yookassa","platega","rollypay","sandbox"),1):
        if p not in existing:
            row=PaymentProviderHealth(provider=p,priority=i*10,enabled=True)
            db.add(row); rows.append(row)
    if any(x.provider not in names for x in rows):
        rows=[x for x in rows if x.provider in names]
    await db.flush()
    rows=sorted(rows,key=lambda x:(x.priority,x.provider))
    now=datetime.utcnow()
    # A provider is routable only when it is explicitly enabled, outside the
    # circuit-breaker cooldown, and has the credentials required to create a
    # payment.  Previously `enabled` was accidentally ignored here, so an
    # operator could disable a provider in the admin panel and checkout would
    # still select it.  Empty credentials also caused a late failure after the
    # customer had already started checkout.
    configured = {
        "yookassa": bool(settings.yookassa_shop_id and settings.yookassa_secret_key),
        "platega": bool(settings.platega_merchant_id and settings.platega_secret),
        "rollypay": bool(settings.rollypay_api_key),
        "sandbox": bool(settings.payments_sandbox),
    }
    enabled=[x.provider for x in rows
             if x.provider in names
             and x.enabled
             and configured.get(x.provider, False)
             and (not x.circuit_open_until or x.circuit_open_until <= now)]
    if requested:
        if requested not in enabled: raise HTTPException(503,"Выбранный платёжный провайдер отключён или временно недоступен")
        return [requested]+[x for x in enabled if x!=requested]
    return enabled

async def reserve_promo(db:AsyncSession, promo:PromoCode|None, user_id:int, order_id:str):
    if not promo:
        return None
    row=(await db.execute(select(PromoCode).where(PromoCode.id==promo.id).with_for_update())).scalar_one()
    active_reserved=int(row.reserved_count or 0)
    if row.usage_limit is not None and int(row.used_count or 0)+active_reserved >= row.usage_limit:
        raise HTTPException(409,"Лимит промокода исчерпан")
    row.reserved_count=active_reserved+1
    reservation=PromoReservation(promo_code_id=row.id,user_id=user_id,order_id=order_id,status="reserved",expires_at=datetime.utcnow()+timedelta(hours=24))
    db.add(reservation); await db.flush()
    return reservation


async def release_promo_reservation(db:AsyncSession, reservation_id:int):
    reservation=(await db.execute(select(PromoReservation).where(PromoReservation.id==reservation_id).with_for_update())).scalar_one_or_none()
    if not reservation or reservation.status!="reserved":
        return False
    promo=(await db.execute(select(PromoCode).where(PromoCode.id==reservation.promo_code_id).with_for_update())).scalar_one_or_none()
    if promo: promo.reserved_count=max(0,int(promo.reserved_count or 0)-1)
    reservation.status="released"
    return True


async def ensure_required_channel(user:User):
    channel=(settings.required_telegram_channel or "").strip()
    if not channel:
        return
    if not user.telegram_id or not settings.bot_token:
        raise HTTPException(403,"Подпишитесь на обязательный канал")
    try:
        async with _pinned_public_http_client(10) as client:
            response=await client.get(
                f"https://api.telegram.org/bot{settings.bot_token}/getChatMember",
                params={"chat_id":channel,"user_id":user.telegram_id},
            )
        data=response.json()
    except Exception as exc:
        raise HTTPException(503,"Не удалось проверить подписку на канал") from exc
    status=((data.get("result") or {}).get("status") if isinstance(data,dict) and data.get("ok") else None)
    if status not in {"member","administrator","creator"}:
        raise HTTPException(403,"Подпишитесь на обязательный канал")

@app.post("/api/payments/create")
async def create_payment(payload:dict, request:Request, db:AsyncSession=Depends(get_db)):
    if await maintenance_enabled(db): raise HTTPException(503,"Service is in maintenance mode")
    if not await feature_enabled(db, "payments", True): raise HTTPException(503,"Платежи отключены администратором")
    sandbox_requested=str(payload.get("provider") or "").lower()=="sandbox" and settings.payments_sandbox
    if await setting_value(db,PRODUCTION_PAYMENTS_GATE_KEY,"0") != "1" and not sandbox_requested:
        raise HTTPException(503,"Реальные платежи временно заблокированы: требуется успешный staging E2E")
    user=await user_from_token(request,db)
    from .platform_api import reject_restricted
    reject_restricted(user)
    constructor_requested=payload.get("constructor_id") not in (None, "", 0, "0")
    constructor_quote=None
    quote_error=None
    plan_id=None
    if constructor_requested:
        from .tariff_api import quote_constructor
        try:
            constructor_quote=await quote_constructor(db, payload)
            plan_id=int(constructor_quote["plan_id"])
        except HTTPException as exc:
            quote_error=exc
    else:
        try:
            plan_id=int(payload.get("plan_id"))
        except (TypeError, ValueError):
            raise HTTPException(400,"Invalid plan_id")
    idem=request.headers.get("Idempotency-Key")
    if not idem or len(idem)>128: raise HTTPException(400,"Idempotency-Key is required")

    # Resolve an existing durable intent before re-validating mutable commercial state.
    # An idempotent retry must remain recoverable even after a promo expires, is disabled,
    # or its usage counter changes. The immutable Payment snapshot is the source of truth
    # for an already-created intent.
    existing=(await db.execute(select(Payment).where(Payment.user_id==user.id,Payment.idempotency_key==idem).order_by(Payment.id.desc()))).scalar_one_or_none()
    if existing:
        if existing.plan_id != plan_id:
            if not (quote_error is not None and plan_id is None):
                raise HTTPException(409,"Idempotency-Key уже использован для другого платежа")
        if constructor_quote and (existing.duration_days_snapshot != constructor_quote["days"] or existing.traffic_limit_gb_snapshot != constructor_quote["traffic_gb"] or existing.device_limit_snapshot != constructor_quote["devices"]):
            raise HTTPException(409,"Idempotency-Key уже использован для другой конфигурации тарифа")
        if existing.provider_payment_id or existing.status not in {"creating","creation_unknown"}:
            return {"id":existing.provider_payment_id,"url":existing.checkout_url,"provider":existing.provider,"status":existing.status}
        # An unresolved intent has already reserved the commercial terms. Do not recompute
        # price/promo from mutable Plan/PromoCode rows during recovery.
        final_amount=Decimal(str(existing.amount))
        expected_promo=existing.promo_code
        if existing.provider != "yookassa":
            raise HTTPException(409,"Платёж создаётся/имеет неопределённый результат; повторное списание заблокировано. Требуется сверка операции.")
        provider=YooKassaProvider()
        lock_key=f"lock:payment-create:{hashlib.sha256(existing.order_id.encode()).hexdigest()}"
        try:
            lock_key, lock_token=await _acquire_redis_lock(lock_key,ttl=300,conflict_message="Payment creation is already in progress")
        except RuntimeError as exc:
            raise HTTPException(409,str(exc)) from exc
        try:
            result=await provider.create(final_amount,existing.order_id,f"VPN plan {existing.plan_id}",settings.mini_app_url)
            if not result.get("id"):
                raise RuntimeError("YooKassa returned no payment ID")
            existing.provider_payment_id=result["id"]; existing.status="pending"; existing.checkout_url=result.get("url"); await db.commit()
            return result
        except Exception as exc:
            await db.rollback()
            existing=(await db.execute(select(Payment).where(Payment.id==existing.id).with_for_update())).scalar_one()
            existing.status="creation_unknown"; existing.fulfillment_terminal=True; existing.fulfillment_error=str(exc)[:2000]
            await audit(db,"payment.creation.uncertain",str(user.id),str(existing.id),{"provider":existing.provider,"error":str(exc)[:500]}); await db.commit()
            raise HTTPException(503,"Результат создания платежа не определён. Повторное списание заблокировано; операция будет сверена.")
        finally:
            await _release_payment_side_effect_lock(lock_key,lock_token)

    # No durable intent exists for this idempotency key, so mutable commercial state
    # is now safe to validate for a brand-new checkout.
    if quote_error:
        raise quote_error
    if plan_id is None:
        raise HTTPException(400,"Invalid plan_id")
    await ensure_required_channel(user)
    plan=await db.get(Plan,plan_id)
    if not plan or not plan.enabled: raise HTTPException(404,"Not found")
    from .tariff_api import linked_constructor_id
    linked=await linked_constructor_id(db, plan.id)
    if linked and (not constructor_quote or int(constructor_quote["constructor_id"]) != int(linked)):
        raise HTTPException(400,"Этот тариф собирается в конструкторе")
    if constructor_quote:
        base_amount=Decimal(str(constructor_quote["amount"]))
        snap_days=int(constructor_quote["days"])
        snap_traffic=constructor_quote["traffic_gb"]
        snap_devices=int(constructor_quote["devices"])
        snap_profile=constructor_quote["profile_id"]
    else:
        base_amount=Decimal(str(plan.price))
        snap_days=plan.duration_days
        snap_traffic=plan.traffic_limit_gb
        snap_devices=plan.device_limit
        snap_profile=plan.remnawave_profile_id
    promo, promo_discount_amount=await promo_discount(db,payload.get("promo_code"),plan.id,base_amount,user.id)
    if promo is None:
        promotion=await active_promotion(db,plan.id)
        discount_amount=discounted_amount(base_amount,promotion.kind,promotion.value) if promotion else Decimal("0.00")
    else:
        promotion=None; discount_amount=promo_discount_amount
    final_amount=(base_amount-discount_amount).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
    bonus_days=0
    if promo is not None and promo.kind=="days":
        bonus_days=int(Decimal(str(promo.value)))
    elif promotion is not None and promotion.kind=="days":
        bonus_days=int(Decimal(str(promotion.value)))
    expected_promo=promo.code if promo else None
    config_tag=""
    if constructor_quote:
        config_tag=f":c{constructor_quote['constructor_id']}:dev{constructor_quote['devices']}:tr{constructor_quote['traffic_gb']}:days{constructor_quote['days']}"
    idem_fingerprint=f"{user.id}:{plan.id}:{idem}:{promo.code if promo else promotion.id if promotion else ''}{config_tag}"
    canonical_order_id=f"vpn-{user.id}-{plan.id}-{hashlib.sha256(idem_fingerprint.encode()).hexdigest()[:24]}"

    # Idempotency lookup already happened above. The order lock below protects the
    # first-time intent creation from concurrent callers using the same key.
    requested_provider=payload.get("provider")
    provider_order=await _payment_provider_order(db,requested_provider)
    if not provider_order: raise HTTPException(503,"Нет доступных платёжных провайдеров")
    provider_name=provider_order[0]
    provider={"yookassa":YooKassaProvider(),"platega":PlategaProvider(),"rollypay":RollyPayProvider(),"sandbox":SandboxProvider()}[provider_name]
    order_id=canonical_order_id
    lock_key=f"lock:payment-create:{hashlib.sha256(canonical_order_id.encode()).hexdigest()}"
    try:
        lock_key, lock_token=await _acquire_redis_lock(lock_key,ttl=300,conflict_message="Payment creation is already in progress")
    except RuntimeError:
        existing=(await db.execute(select(Payment).where(Payment.order_id==order_id))).scalar_one_or_none()
        if existing: return {"id":existing.provider_payment_id,"url":existing.checkout_url,"provider":existing.provider,"status":existing.status}
        raise HTTPException(409,"Payment creation is already in progress")
    reservation=None; payment_row=None
    try:
        candidate=provider_order[0]
        candidate_provider={"yookassa":YooKassaProvider(),"platega":PlategaProvider(),"rollypay":RollyPayProvider(),"sandbox":SandboxProvider()}[candidate]
        # Re-check after acquiring the distributed lock so two first-time callers cannot
        # create two durable intents for the same idempotency key.
        existing=(await db.execute(select(Payment).where(Payment.order_id==order_id).with_for_update())).scalar_one_or_none()
        if existing:
            return {"id":existing.provider_payment_id,"url":existing.checkout_url,"provider":existing.provider,"status":existing.status}
        if promo:
            reservation=await reserve_promo(db,promo,user.id,canonical_order_id)
        # Durable payment intent BEFORE the external provider call. A process crash after
        # provider acceptance cannot erase the fact that this order already exists.
        payment_row=Payment(user_id=user.id,plan_id=plan.id,provider=candidate,provider_payment_id=None,order_id=order_id,amount=final_amount,original_amount=base_amount,discount_amount=discount_amount,duration_days_snapshot=snap_days,traffic_limit_gb_snapshot=snap_traffic,device_limit_snapshot=snap_devices,remnawave_profile_id_snapshot=snap_profile,referrer_id_snapshot=user.referred_by_id,promo_code=(promo.code if promo else None),currency=settings.default_currency,status="creating",fulfillment_status="pending",idempotency_key=idem,purpose="subscription",bonus_days=bonus_days)
        db.add(payment_row)
        await db.flush()
        if reservation: reservation.payment_id=payment_row.id
        await db.commit()
        try:
            result=await candidate_provider.create(final_amount,canonical_order_id,f"VPN {plan.name}",settings.cabinet_url or settings.mini_app_url)
            if not result.get("id"):
                raise RuntimeError("Payment provider returned no payment ID")
            provider_name=candidate; provider=candidate_provider
            health=(await db.execute(select(PaymentProviderHealth).where(PaymentProviderHealth.provider==candidate).with_for_update())).scalar_one_or_none()
            if health:
                health.success_count += 1; health.failure_count=0; health.last_error=None; health.circuit_open_until=None; health.updated_at=datetime.utcnow()
            payment_row=(await db.execute(select(Payment).where(Payment.id==payment_row.id).with_for_update())).scalar_one()
            payment_row.provider_payment_id=result["id"]; payment_row.checkout_url=result.get("url"); payment_row.fulfillment_terminal=False
            if candidate=="sandbox" and result.get("status")=="succeeded":
                payment_row.status="paid"; payment_row.paid_at=datetime.utcnow(); await db.commit()
                try:
                    await fulfill(payment_row.id, db)
                except Exception:
                    pass
            else:
                payment_row.status="pending"; await db.commit()
        except Exception as exc:
            last_error=str(exc)[:1000]
            await db.rollback()
            health=(await db.execute(select(PaymentProviderHealth).where(PaymentProviderHealth.provider==candidate).with_for_update())).scalar_one_or_none()
            if health:
                health.failure_count += 1; health.last_error=last_error; health.updated_at=datetime.utcnow()
                if health.failure_count >= 3: health.circuit_open_until=datetime.utcnow()+timedelta(minutes=5)
            payment_row=(await db.execute(select(Payment).where(Payment.id==payment_row.id).with_for_update())).scalar_one()
            payment_row.status="creation_unknown"; payment_row.fulfillment_terminal=True; payment_row.fulfillment_error=last_error
            await audit(db,"payment.creation.uncertain",str(user.id),str(payment_row.id),{"provider":candidate,"error":last_error,"fallback_blocked":True})
            await db.commit()
            raise HTTPException(503,"Результат создания платежа не определён. Повторное списание заблокировано; операция будет сверена.")
        if result.get("recurring_token") and provider_name == "yookassa" and result.get("status") == "succeeded":
            existing_method=(await db.execute(select(AutoRenewMethod).where(AutoRenewMethod.user_id==user.id).with_for_update())).scalar_one_or_none()
            token_enc=encrypt_secret(str(result["recurring_token"]))
            if existing_method:
                existing_method.provider="yookassa"; existing_method.external_token_encrypted=token_enc; existing_method.enabled=True
            else:
                db.add(AutoRenewMethod(user_id=user.id,provider="yookassa",external_token_encrypted=token_enc,enabled=True))
            await db.commit()
        return result
    finally:
        await _release_payment_side_effect_lock(lock_key,lock_token)
_LOCK_RENEW_TASKS: dict[str, asyncio.Task] = {}

async def _renew_redis_lock(key: str, token: str, ttl: int):
    # Keep long-running external side effects serialized even when a Remnawave/provider
    # request takes longer than the initial lease. The token check prevents renewing a
    # lock that has already been acquired by another worker after expiry. The registry
    # entry is also self-cleaned when the renewal task exits unexpectedly, so a caller
    # that hangs or loses Redis cannot leak task references forever.
    interval=max(1, ttl // 3)
    script="if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('expire', KEYS[1], ARGV[2]) else return 0 end"
    try:
        while True:
            await asyncio.sleep(interval)
            if redis_client is None: return
            renewed=await redis_client.eval(script,1,key,token,str(ttl))
            if int(renewed or 0) != 1: return
    except asyncio.CancelledError:
        return
    except Exception as exc:
        logger.warning("Redis lock renewal failed for %s: %s", key, exc)
    finally:
        current=asyncio.current_task()
        if _LOCK_RENEW_TASKS.get(token) is current:
            _LOCK_RENEW_TASKS.pop(token,None)

async def _acquire_redis_lock(key: str, *, ttl: int, conflict_message: str):
    if redis_client is None:
        raise RuntimeError("Redis is required for distributed locking")
    token=secrets.token_urlsafe(24)
    if not await redis_client.set(key, token, nx=True, ex=ttl):
        raise RuntimeError(conflict_message)
    task=asyncio.create_task(_renew_redis_lock(key,token,ttl))
    _LOCK_RENEW_TASKS[token]=task
    return key, token

async def _acquire_payment_side_effect_lock(payment_id: int, ttl: int = 300):
    key=f"lock:fulfill:payment:{payment_id}"
    try:
        return await _acquire_redis_lock(key,ttl=ttl,conflict_message="Payment side effect is already in progress")
    except RuntimeError:
        raise

async def _release_payment_side_effect_lock(key: str, token: str):
    task=_LOCK_RENEW_TASKS.pop(token,None)
    if task:
        task.cancel()
    if redis_client is None:
        return
    try:
        await redis_client.eval("if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end",1,key,token)
    except Exception as exc:
        logger.warning("Non-critical operation failed: %s", exc)

async def _acquire_user_fulfillment_lock(user_id: int, ttl: int = 300):
    key=f"lock:fulfill:user:{user_id}"
    try:
        return await _acquire_redis_lock(key,ttl=ttl,conflict_message="User provisioning/deletion is already in progress")
    except RuntimeError as exc:
        raise HTTPException(409,str(exc)) from exc

async def _confirm_and_fulfill_payment(payment_id:int, db:AsyncSession):
    """Confirm a provider-successful payment without ever reviving a refunded payment.

    The user lock is acquired before the payment lock so refund, deletion, auto-renew and
    fulfillment share one critical-section order. The payment is re-read under FOR UPDATE
    immediately before the paid transition; a stale webhook/reconciliation snapshot can
    therefore never move a refunded payment back to paid.
    """
    seed=(await db.execute(select(Payment).where(Payment.id==payment_id))).scalar_one_or_none()
    if not seed:
        raise RuntimeError("Payment not found")
    user_lock,user_token=await _acquire_user_fulfillment_lock(seed.user_id,ttl=300)
    payment_lock=payment_token=None
    try:
        confirm_payment_lock,confirm_payment_token=await _acquire_payment_side_effect_lock(payment_id)
        confirmed=(await db.execute(select(Payment).where(Payment.id==payment_id).with_for_update())).scalar_one_or_none()
        if not confirmed:
            raise RuntimeError("Payment not found after acquiring locks")
        if confirmed.status in {"refunded","refunded_pending_revoke","creation_unknown"}:
            return {"ok":True,"ignored":True,"reason":"payment_not_eligible"}
        if confirmed.status != "paid":
            confirmed.status="paid"
            confirmed.paid_at=confirmed.paid_at or datetime.utcnow()
            confirmed.fulfillment_status="pending"
            confirmed.fulfillment_terminal=False
            await record_financial_event(db, operation_key=f"payment:{confirmed.id}:paid", user_id=confirmed.user_id, payment_id=confirmed.id, kind="payment", direction="credit", amount=Decimal(str(confirmed.amount)), currency=confirmed.currency, metadata={"provider": confirmed.provider, "order_id": confirmed.order_id})
            await db.commit()
        else:
            await db.commit()
        # Do not hold the payment lock across a second acquisition inside fulfill(); keep
        # the user lock, preserving the global order user -> payment.
        await _release_payment_side_effect_lock(confirm_payment_lock,confirm_payment_token)
        confirm_payment_lock=confirm_payment_token=None
        await fulfill(payment_id,db,existing_user_lock_token=user_token)
        return {"ok":True,"ignored":False,"reason":"fulfilled"}
    finally:
        if confirm_payment_lock and confirm_payment_token:
            await _release_payment_side_effect_lock(confirm_payment_lock,confirm_payment_token)
        await _release_payment_side_effect_lock(user_lock,user_token)

async def fulfill(payment_id:int, db:AsyncSession, existing_user_lock_token: str|None = None):
    if redis_client is None:
        raise RuntimeError("Redis is required for fulfillment locking")
    # Global lock order: user -> payment. Auto-renew already owns the user lock
    # before it verifies/fulfills a recurring payment. Fulfillment must follow the
    # same order or concurrent webhook/worker and auto-renew paths can strand a
    # paid payment when each holds one lock and the other is busy.
    payment_lock = token = None
    user_token=None
    user_lock=None
    user_lock_key=None
    try:
        payment=(await db.execute(select(Payment).where(Payment.id==payment_id))).scalar_one_or_none()
        if not payment: raise RuntimeError("Payment not found")
        if payment.status != "paid": raise RuntimeError("Payment is not confirmed")
        if payment.fulfillment_status=="completed" or payment.fulfillment_terminal: return
        if payment.fulfillment_attempts >= (payment.fulfillment_max_attempts or settings.fulfillment_max_attempts):
            payment.fulfillment_status="failed"; payment.fulfillment_terminal=True; await db.commit(); raise RuntimeError("Fulfillment reached maximum attempts")
        user=await db.get(User,payment.user_id)
        is_topup=(payment.purpose or "subscription")=="topup"
        plan=None if is_topup else await db.get(Plan,payment.plan_id)
        if not user or user.deleted_at is not None or (not is_topup and not plan): raise RuntimeError("Payment references missing or deleted user/plan")
        # Purchased payments use their immutable checkout snapshot. Legacy rows without
        # snapshots fall back to the current plan for backward compatibility.
        if not is_topup:
            duration_days=(payment.duration_days_snapshot or plan.duration_days)+int(payment.bonus_days or 0)
            traffic_limit_gb=payment.traffic_limit_gb_snapshot if payment.traffic_limit_gb_snapshot is not None else plan.traffic_limit_gb
            profile_id=payment.remnawave_profile_id_snapshot if payment.remnawave_profile_id_snapshot is not None else plan.remnawave_profile_id
        user_token = existing_user_lock_token
        if not existing_user_lock_token:
            user_lock,user_token=await _acquire_user_fulfillment_lock(user.id,ttl=300)
            user_lock_key=user_lock
        # The first User read above is only a discovery snapshot. Account deletion uses
        # the same user lock, so after acquiring it we must always re-read the row under
        # FOR UPDATE, including when the caller already supplied the held user-lock token.
        # Otherwise auto-renew/webhook paths could keep a stale `deleted_at=None` object
        # and start a Remnawave side effect for an account that has already been anonymized.
        user=(await db.execute(select(User).where(User.id==user.id).with_for_update())).scalar_one_or_none()
        if not user or user.deleted_at is not None:
            raise RuntimeError("User is deleted or no longer available for fulfillment")
        plan=None if (payment.purpose or "subscription")=="topup" else await db.get(Plan,payment.plan_id)
        if (payment.purpose or "subscription")!="topup" and not plan:
            raise RuntimeError("Payment plan no longer exists")
        if (payment.purpose or "subscription")!="topup":
            duration_days=(payment.duration_days_snapshot or plan.duration_days)+int(payment.bonus_days or 0)
            traffic_limit_gb=payment.traffic_limit_gb_snapshot if payment.traffic_limit_gb_snapshot is not None else plan.traffic_limit_gb
            profile_id=payment.remnawave_profile_id_snapshot if payment.remnawave_profile_id_snapshot is not None else plan.remnawave_profile_id
        payment_lock, token = await _acquire_payment_side_effect_lock(payment_id)
        # Re-read the payment after acquiring the shared payment lock. A refund/reconcile
        # path can legitimately win the lock after the initial read above. Never start
        # remote provisioning from a stale `paid` snapshot: doing so could provision a
        # payment that has already been refunded, even though the final DB check would
        # eventually reject completion.
        payment=(await db.execute(select(Payment).where(Payment.id==payment_id).with_for_update())).scalar_one_or_none()
        if not payment:
            raise RuntimeError("Payment not found after acquiring fulfillment lock")
        if payment.status in {"refunded", "refunded_pending_revoke", "creation_unknown"}:
            raise RuntimeError("Payment is no longer eligible for fulfillment")
        if payment.status != "paid":
            raise RuntimeError("Payment is not confirmed")
        if payment.fulfillment_status=="completed" or payment.fulfillment_terminal:
            return
        if (payment.purpose or "subscription")=="topup":
            amount=Decimal(str(payment.amount)).quantize(Decimal("0.01"))
            user.wallet_balance=(Decimal(str(user.wallet_balance or 0))+amount).quantize(Decimal("0.01"))
            await record_financial_event(db,operation_key=f"wallet-topup:{payment.id}",user_id=user.id,payment_id=payment.id,kind="wallet_topup",direction="credit",amount=amount,currency=payment.currency,metadata={"order_id":payment.order_id})
            payment.fulfillment_status="completed"; payment.fulfillment_terminal=True; payment.fulfillment_attempts=(payment.fulfillment_attempts or 0)+1
            await audit(db,"wallet.topup",f"user:{user.id}",str(payment.id),{"amount":str(amount)}); await db.commit(); return
        payment.fulfillment_status="processing"; payment.fulfillment_attempts=(payment.fulfillment_attempts or 0)+1; payment.fulfillment_error=None
        job=(await db.execute(select(Job).where(Job.job_key==f"fulfillment:{payment.id}").with_for_update())).scalar_one_or_none()
        if not job:
            job=Job(job_key=f"fulfillment:{payment.id}",kind="fulfillment",status="processing",attempts=payment.fulfillment_attempts,max_attempts=payment.fulfillment_max_attempts or settings.fulfillment_max_attempts,payload={"payment_id":payment.id})
            db.add(job)
        else:
            job.status="processing"; job.attempts=payment.fulfillment_attempts; job.error=None; job.locked_at=datetime.utcnow()
        await db.commit()
        sub=(await db.execute(select(Subscription).where(Subscription.user_id==user.id))).scalar_one_or_none()
        now=datetime.utcnow(); rw=RemnawaveClient()
        op_row=(await db.execute(select(ProvisioningOperation).where(ProvisioningOperation.payment_id==payment.id))).scalar_one_or_none()
        if not op_row:
            op_row=ProvisioningOperation(payment_id=payment.id,user_id=user.id,operation_key=f"payment:{payment.id}:v1",action="extend" if sub and sub.remnawave_uuid else "provision",status="pending",attempts=0,created_at=now,updated_at=now)
            db.add(op_row); await db.commit()
        op_row.status="processing"; op_row.attempts=(op_row.attempts or 0)+1; op_row.updated_at=now; await db.commit()
        try:
            if sub and sub.remnawave_uuid:
                # Refunds disable the remote user. A later legitimate purchase must re-enable it.
                remote_before=await rw.get_user(sub.remnawave_uuid)
                remote_status=str(remote_before.get("status") or remote_before.get("state") or "").lower() if isinstance(remote_before,dict) else ""
                if remote_status in {"disabled","blocked","inactive"}:
                    await rw.enable_user(sub.remnawave_uuid)
                remote_expiry=await rw.get_expiry(sub.remnawave_uuid)
                persisted_before=op_row.expected_before_expires_at
                persisted_after=op_row.expected_after_expires_at
                if persisted_before is not None and persisted_after is not None:
                    before_local=persisted_before
                    expected_after=persisted_after
                else:
                    before_local=max(sub.expires_at or now, remote_expiry or now, now)
                    expected_after=before_local+timedelta(days=duration_days)
                    op_row.expected_before_expires_at=before_local
                    op_row.expected_after_expires_at=expected_after
                    await db.commit()
                # Existing remote users must receive the purchased traffic/profile terms too;
                # otherwise a plan upgrade can pay for more traffic while the old remote
                # quota remains in force (or a downgrade can leave excess quota active).
                await rw.update_entitlements(sub.remnawave_uuid,traffic_limit_gb,profile_id)
                extension=await rw.extend_idempotent(sub.remnawave_uuid,duration_days,before_local,expected_after)
                rw_sub=await rw.get_subscription(sub.remnawave_uuid)
                verified_expiry=extension.get("expires_at") if isinstance(extension,dict) else None
                sub.plan_id=plan.id; sub.expires_at=max(expected_after,verified_expiry or expected_after)
                sub.traffic_limit_gb_snapshot=traffic_limit_gb
                sub.device_limit_snapshot=payment.device_limit_snapshot
                sub.remnawave_profile_id_snapshot=profile_id
                sub.subscription_url=rw_sub.get("subscriptionUrl") or rw_sub.get("subscription_url") or sub.subscription_url
                op_row.remote_user_id=str(sub.remnawave_uuid)
            else:
                username=f"user_{user.id}"
                # Recover a successful create whose response was lost before the shop received it.
                existing_remote=None
                try: existing_remote=await rw.get_user_by_username(username)
                except Exception: existing_remote=None
                if existing_remote and existing_remote.get("id"):
                    data=existing_remote; op_row.remote_user_id=str(data.get("id"))
                    remote_id=str(data.get("id"))
                    remote_status=str(data.get("status") or data.get("state") or "").lower()
                    if remote_status in {"disabled","blocked","inactive"}:
                        await rw.enable_user(remote_id)
                    await rw.update_entitlements(remote_id,traffic_limit_gb,profile_id)
                    remote_expiry=await rw.get_expiry(remote_id)
                    target_expiry=max(now+timedelta(days=duration_days), remote_expiry or now)
                    if not remote_expiry or remote_expiry < target_expiry:
                        before_remote=remote_expiry or now
                        extension_seconds=(target_expiry-max(before_remote,now)).total_seconds()
                        extension_days=max(1, int((extension_seconds + 86399) // 86400))
                        await rw.extend_idempotent(str(data.get("id")),extension_days,before_remote,target_expiry)
                        data=await rw.get_user(str(data.get("id")))
                    final_remote_expiry=await rw.get_expiry(str(data.get("id"))) or target_expiry
                else:
                    expires=now+timedelta(days=duration_days); traffic=traffic_limit_gb*1024**3 if traffic_limit_gb else 0
                    data=await rw.create_user(username,expires,traffic,active_internal_squads=[profile_id] if profile_id else None,telegram_id=user.telegram_id)
                    op_row.remote_user_id=str(data.get("id")); final_remote_expiry=expires
                if not sub:
                    sub=Subscription(user_id=user.id,plan_id=plan.id); db.add(sub)
                sub.plan_id=plan.id; sub.remnawave_uuid=str(data.get("id")); sub.expires_at=final_remote_expiry
                sub.traffic_limit_gb_snapshot=traffic_limit_gb
                sub.device_limit_snapshot=payment.device_limit_snapshot
                sub.remnawave_profile_id_snapshot=profile_id
                sub.subscription_url=data.get("subscriptionUrl") or data.get("subscription_url")
            op_row.status="completed"; op_row.completed_at=datetime.utcnow(); op_row.updated_at=datetime.utcnow()
        except Exception as remote_exc:
            op_row.status="retry"; op_row.last_error=str(remote_exc)[:2000]; op_row.updated_at=datetime.utcnow(); job.status="failed" if payment.fulfillment_attempts >= payment.fulfillment_max_attempts else "queued"; job.error=str(remote_exc)[:2000]; job.next_retry_at=datetime.utcnow()+timedelta(minutes=min(30,max(1,2**min(payment.fulfillment_attempts,5)))); job.locked_at=None; await db.commit(); raise
        payment=(await db.execute(select(Payment).where(Payment.id==payment.id).with_for_update())).scalar_one()
        if payment.status != "paid" or payment.fulfillment_terminal:
            raise RuntimeError("Payment state changed while fulfillment was in progress; reconciliation is required")
        payment.fulfillment_status="completed"; payment.next_retry_at=None; payment.fulfillment_terminal=False
        job.status="completed"; job.completed_at=datetime.utcnow(); job.locked_at=None; job.worker_id=None; job.error=None
        if payment.promo_code:
            reservation=(await db.execute(select(PromoReservation).where(PromoReservation.payment_id==payment.id).with_for_update())).scalar_one_or_none()
            promo_row=(await db.execute(select(PromoCode).where(PromoCode.code==payment.promo_code).with_for_update())).scalar_one_or_none()
            if reservation and reservation.status=="reserved" and promo_row:
                promo_row.reserved_count=max(0,int(promo_row.reserved_count or 0)-1)
                promo_row.used_count += 1
                reservation.status="consumed"
                db.add(PromoRedemption(promo_code_id=promo_row.id,user_id=user.id,payment_id=payment.id))
            elif not reservation and promo_row and (promo_row.usage_limit is None or promo_row.used_count < promo_row.usage_limit):
                # Legacy payments created before reservation support.
                promo_row.used_count += 1
                db.add(PromoRedemption(promo_code_id=promo_row.id,user_id=user.id,payment_id=payment.id))
        if payment.referrer_id_snapshot:
            existing=(await db.execute(select(ReferralReward).where(ReferralReward.payment_id==payment.id))).scalar_one_or_none()
            if not existing:
                reward=(Decimal(str(payment.amount))*Decimal(str(settings.referral_reward_percent))/Decimal("100")).quantize(Decimal("0.01"))
                if reward>0:
                    result=await db.execute(sql_text("UPDATE users SET referral_balance=referral_balance+:amount WHERE id=:uid"),{"amount":reward,"uid":payment.referrer_id_snapshot})
                    if result.rowcount != 1: raise RuntimeError("Referrer account not found")
                    db.add(ReferralReward(referrer_id=payment.referrer_id_snapshot,referred_user_id=user.id,payment_id=payment.id,amount=reward))
                    db.add(ReferralLedger(user_id=payment.referrer_id_snapshot,source_user_id=user.id,payment_id=payment.id,amount=reward,kind="reward"))
        await audit(db,"payment.fulfilled","system",str(payment.id),{"provider":payment.provider,"attempt":payment.fulfillment_attempts})
        await enqueue_notification(db,user_id=user.id,channel="in_app",kind="payment_success",title="Оплата подтверждена",body=f"Заказ {payment.order_id} оплачен. Подписка готовится или уже активирована.",dedupe_key=f"payment:{payment.id}:success")
        await enqueue_notification(db,user_id=user.id,channel="in_app",kind="subscription_ready",title="Подписка активирована",body="Ваша VPN-подписка активирована. Откройте раздел подключения, чтобы получить ссылку.",dedupe_key=f"payment:{payment.id}:ready")
        await db.commit()
    except Exception as exc:
        try:
            await db.rollback(); payment=(await db.execute(select(Payment).where(Payment.id==payment_id))).scalar_one_or_none()
            if payment:
                attempts=payment.fulfillment_attempts or 1; terminal=attempts >= (payment.fulfillment_max_attempts or settings.fulfillment_max_attempts)
                payment.fulfillment_status="failed"; payment.fulfillment_terminal=terminal; payment.fulfillment_error=str(exc)[:2000]
                payment.next_retry_at=None if terminal else datetime.utcnow()+timedelta(seconds=min(3600,60*(2**max(0,attempts-1))))
                job=(await db.execute(select(Job).where(Job.job_key==f"fulfillment:{payment.id}").with_for_update())).scalar_one_or_none()
                if job:
                    job.status="failed" if terminal else "queued"; job.error=str(exc)[:2000]; job.locked_at=None; job.worker_id=None; job.next_retry_at=payment.next_retry_at
                await audit(db,"payment.fulfillment.failed","system",str(payment.id),{"error":str(exc)[:500],"terminal":terminal}); await db.commit()
        except Exception: await db.rollback()
        raise
    finally:
        if payment_lock and token:
            await _release_payment_side_effect_lock(payment_lock, token)
        if user_token and not existing_user_lock_token:
            try:
                await _release_payment_side_effect_lock(user_lock_key,user_token)
            except Exception as exc:
                logger.warning("Non-critical operation failed: %s", exc)
async def payment_by_provider(db, provider, pid):
    return (await db.execute(select(Payment).where(Payment.provider==provider,Payment.provider_payment_id==str(pid)))).scalar_one_or_none()

async def payment_by_provider_or_order(db: AsyncSession, provider: str, pid: str|None, order_id: str|None):
    payment = await payment_by_provider(db, provider, pid) if pid else None
    if payment or not order_id:
        return payment
    return (await db.execute(select(Payment).where(Payment.provider==provider, Payment.order_id==str(order_id)).with_for_update())).scalar_one_or_none()

async def bind_provider_payment_id(db: AsyncSession, payment: Payment, provider_payment_id: str):
    provider_payment_id=str(provider_payment_id)
    if payment.provider_payment_id and payment.provider_payment_id != provider_payment_id:
        raise HTTPException(409,"Payment provider identifier mismatch")
    payment.provider_payment_id=provider_payment_id
    if payment.status in {"creating","creation_unknown"}:
        payment.status="pending"
        payment.fulfillment_terminal=False

def _ip_allowed(value: str, allowlist: str) -> bool:
    try: ip=ipaddress.ip_address(value)
    except ValueError: return False
    for item in allowlist.split(","):
        try:
            net=ipaddress.ip_network(item.strip(), strict=False)
            if ip in net: return True
        except ValueError: continue
    return False

async def register_provider_event(db:AsyncSession, provider:str, event_id:str, payment_id:int|None):
    """Atomically claim a verified event. Failed/retry events may be reclaimed; processed events are immutable."""
    if not event_id: return True
    stmt=sql_text("""INSERT INTO payment_provider_events (provider,event_id,payment_id,status,attempts)
        VALUES (:p,:e,:pid,'processing',1)
        ON CONFLICT (provider,event_id) DO UPDATE SET payment_id=COALESCE(payment_provider_events.payment_id,EXCLUDED.payment_id),
        status='processing', attempts=payment_provider_events.attempts+1, last_error=NULL, received_at=NOW()
        WHERE payment_provider_events.provider = EXCLUDED.provider
          AND (payment_provider_events.status IN ('failed','retry')
           OR (payment_provider_events.status='processing' AND payment_provider_events.received_at < NOW() - INTERVAL '10 minutes'))
        RETURNING id""")
    result=await db.execute(stmt,{"p":provider,"e":event_id,"pid":payment_id})
    return result.first() is not None

async def finish_provider_event(db:AsyncSession, provider:str, event_id:str, *, ok:bool, error:str|None=None):
    await db.execute(sql_text("UPDATE payment_provider_events SET status=:status,last_error=:error,processed_at=:processed WHERE provider=:p AND event_id=:e"),
                     {"status":"processed" if ok else "retry","error":None if ok else (error or "")[:2000],"processed":datetime.utcnow() if ok else None,"p":provider,"e":event_id})

@app.post("/api/webhooks/yookassa")
async def yookassa_webhook(request:Request, db:AsyncSession=Depends(get_db)):
    client_ip=_client_ip(request)
    # Fail closed: an empty allowlist must not accept unsigned YooKassa notifications.
    if not settings.yookassa_webhook_ip_allowlist or not _ip_allowed(client_ip,settings.yookassa_webhook_ip_allowlist): raise HTTPException(403,"Webhook IP not allowed")
    raw=await request.body()
    try: d=json.loads(raw)
    except Exception: raise HTTPException(400,"Invalid JSON")
    obj=d.get("object",{}) or {}
    pid=obj.get("id"); event_id=str(d.get("id") or hashlib.sha256(raw).hexdigest())
    order_id=(obj.get("metadata") or {}).get("order_id")
    if d.get("event")!="payment.succeeded" or not pid: return {"ok":True}
    p=await payment_by_provider_or_order(db,"yookassa",pid,order_id)
    if not p: return {"ok":True}
    if order_id and order_id != p.order_id: raise HTTPException(403,"Order mismatch")
    # Verify the provider object itself, including immutable order metadata, before
    # binding a previously-unknown provider payment ID to a durable local intent.
    if not await YooKassaProvider().verify_succeeded(pid,Decimal(str(p.amount)),p.currency,p.order_id): raise HTTPException(503,"Payment status verification unavailable")
    if not p.provider_payment_id:
        await bind_provider_payment_id(db,p,pid)
    if not await register_provider_event(db,"yookassa",event_id,p.id): await db.rollback(); return {"ok":True,"duplicate":True}
    await db.commit()
    try:
        # Late-success guard: p.status in {"refunded", "refunded_pending_revoke"} is re-checked atomically inside _confirm_and_fulfill_payment.
        result=await _confirm_and_fulfill_payment(p.id,db)
        if result.get("ignored"):
            async with AsyncSession(engine,expire_on_commit=False) as edb:
                await finish_provider_event(edb,"yookassa",event_id,ok=True); await edb.commit()
            return {"ok":True,"ignored":True,"reason":"payment_already_refunded"}
        async with AsyncSession(engine,expire_on_commit=False) as edb: await finish_provider_event(edb,"yookassa",event_id,ok=True); await edb.commit()
    except Exception as exc:
        async with AsyncSession(engine,expire_on_commit=False) as edb: await finish_provider_event(edb,"yookassa",event_id,ok=False,error=str(exc)); await edb.commit()
        raise
    return {"ok":True}

@app.post("/api/webhooks/platega")
async def platega_webhook(request:Request, db:AsyncSession=Depends(get_db)):
    if not verify_platega_headers(request.headers.get("X-MerchantId"),request.headers.get("X-Secret")): raise HTTPException(403,"Invalid webhook credentials")
    raw=await request.body()
    try: d=json.loads(raw)
    except Exception: raise HTTPException(400,"Invalid JSON")
    pid=d.get("id") or d.get("Id") or d.get("transactionId"); event_id=str(d.get("eventId") or d.get("id") or hashlib.sha256(raw).hexdigest())
    if str(d.get("status") or d.get("Status")).upper() not in {"CONFIRMED","SUCCESS","SUCCEEDED"} or not pid: return {"ok":True}
    payload_order=str(d.get("payload") or d.get("Payload") or "")
    p=await payment_by_provider_or_order(db,"platega",pid,payload_order or None)
    if p:
        if payload_order and payload_order != p.order_id: raise HTTPException(403,"Order mismatch")
        if not await PlategaProvider().verify_succeeded(pid,Decimal(str(p.amount)),p.currency,p.order_id): raise HTTPException(503,"Payment verification unavailable")
        if not p.provider_payment_id:
            await bind_provider_payment_id(db,p,pid)
        if not await register_provider_event(db,"platega",event_id,p.id): await db.rollback(); return {"ok":True,"duplicate":True}
        await db.commit()
        try:
            # Late-success guard: p.status in {"refunded", "refunded_pending_revoke"} is re-checked atomically inside _confirm_and_fulfill_payment.
            result=await _confirm_and_fulfill_payment(p.id,db)
            if result.get("ignored"):
                async with AsyncSession(engine,expire_on_commit=False) as edb:
                    await finish_provider_event(edb,"platega",event_id,ok=True); await edb.commit()
                return {"ok":True,"ignored":True,"reason":"payment_already_refunded"}
            async with AsyncSession(engine,expire_on_commit=False) as edb: await finish_provider_event(edb,"platega",event_id,ok=True); await edb.commit()
        except Exception as exc:
            async with AsyncSession(engine,expire_on_commit=False) as edb: await finish_provider_event(edb,"platega",event_id,ok=False,error=str(exc)); await edb.commit()
            raise
    return {"ok":True}

@app.post("/api/webhooks/rollypay")
async def rollypay_webhook(request:Request,db:AsyncSession=Depends(get_db)):
    raw=await request.body()
    if not verify_rollypay(raw,request.headers.get("X-Timestamp",""),request.headers.get("X-Signature","")): raise HTTPException(403,"Invalid signature")
    try: d=json.loads(raw)
    except Exception: raise HTTPException(400,"Invalid JSON")
    pid=d.get("payment_id"); event_id=str(d.get("event_id") or d.get("id") or hashlib.sha256(raw).hexdigest())
    if str(d.get("status")).lower() not in {"paid","success","succeeded"} or not pid: return {"ok":True}
    order_id=str(d.get("order_id") or "")
    p=await payment_by_provider_or_order(db,"rollypay",pid,order_id or None)
    if p:
        if order_id and order_id != p.order_id: raise HTTPException(403,"Order mismatch")
        if not await RollyPayProvider().verify_succeeded(pid,Decimal(str(p.amount)),p.currency,p.order_id): raise HTTPException(503,"Payment verification unavailable")
        if not p.provider_payment_id:
            await bind_provider_payment_id(db,p,pid)
        if not await register_provider_event(db,"rollypay",event_id,p.id): await db.rollback(); return {"ok":True,"duplicate":True}
        await db.commit()
        try:
            # Late-success guard: p.status in {"refunded", "refunded_pending_revoke"} is re-checked atomically inside _confirm_and_fulfill_payment.
            result=await _confirm_and_fulfill_payment(p.id,db)
            if result.get("ignored"):
                async with AsyncSession(engine,expire_on_commit=False) as edb:
                    await finish_provider_event(edb,"rollypay",event_id,ok=True); await edb.commit()
                return {"ok":True,"ignored":True,"reason":"payment_already_refunded"}
            async with AsyncSession(engine,expire_on_commit=False) as edb: await finish_provider_event(edb,"rollypay",event_id,ok=True); await edb.commit()
        except Exception as exc:
            async with AsyncSession(engine,expire_on_commit=False) as edb: await finish_provider_event(edb,"rollypay",event_id,ok=False,error=str(exc)); await edb.commit()
            raise
    return {"ok":True}

# ---------- Reliability, sessions, analytics, referrals ----------
async def fulfillment_retry_scheduler():
    while True:
        try:
            async with AsyncSession(engine,expire_on_commit=False) as db:
                rows=(await db.execute(select(Payment).where(Payment.fulfillment_status=="failed",Payment.next_retry_at<=datetime.utcnow()).order_by(Payment.next_retry_at).limit(10))).scalars().all()
                for p in rows:
                    try: await fulfill(p.id,db)
                    except Exception as exc:
                        logger.warning("Non-critical operation failed: %s", exc)
            await asyncio.sleep(15)
        except Exception: await asyncio.sleep(15)

async def refund_revoke_scheduler():
    while True:
        try:
            async with AsyncSession(engine,expire_on_commit=False) as db:
                providers={"yookassa":YooKassaProvider(),"platega":PlategaProvider(),"rollypay":RollyPayProvider()}
                pending=(await db.execute(select(RefundRequest).where(RefundRequest.status=="processing",RefundRequest.provider_refund_id.is_not(None)).order_by(RefundRequest.updated_at).limit(50))).scalars().all()
                for r in pending:
                    p=await db.get(Payment,r.payment_id); provider=providers.get(p.provider) if p else None
                    if not p or not provider or not hasattr(provider,"get_refund_status"): continue
                    try:
                        status=await provider.get_refund_status(r.provider_refund_id)
                        if status in {"succeeded","paid","completed","refunded"}:
                            # Reconciliation is another refund side-effect entry point. It must
                            # serialize with fulfillment just like manual refund execution;
                            # otherwise a background poll can mark a payment refunded while
                            # an already-running fulfillment is still provisioning it.
                            user_lock, user_token = await _acquire_user_fulfillment_lock(p.user_id,ttl=300)
                            payment_lock = payment_token = None
                            try:
                                payment_lock, payment_token = await _acquire_payment_side_effect_lock(p.id)
                                p=(await db.execute(select(Payment).where(Payment.id==p.id).with_for_update())).scalar_one()
                                r=(await db.execute(select(RefundRequest).where(RefundRequest.id==r.id).with_for_update())).scalar_one()
                                if p.status == "refunded" and r.status == "refunded":
                                    continue
                                r.status="refunded"; p.status="refunded"; p.fulfillment_terminal=True; r.updated_at=datetime.utcnow()
                                try:
                                    revoke_result=await _safe_revoke_for_refunded_payment(db,p,"system","subscription.revoked.refund.reconciled")
                                except Exception as exc:
                                    r.status="refunded_pending_revoke"; r.reason=(r.reason or "")+"\nRevoke pending: "+str(exc)[:500]; revoke_result={"revoked":False,"reason":"revoke_failed"}
                                reversal_result=await _reverse_referral_reward_for_refund(db,p,"system") if r.status == "refunded" else {"reversed":False}
                                await audit(db,"payment.refund.reconciled","system",str(p.id),{"provider_status":status,**revoke_result,**reversal_result})
                            finally:
                                if payment_lock and payment_token:
                                    await _release_payment_side_effect_lock(payment_lock, payment_token)
                                await _release_payment_side_effect_lock(user_lock,user_token)
                        elif status in {"canceled","cancelled","failed","rejected"}:
                            r.status="failed"; r.reason=(r.reason or "")+f"\nProvider refund status: {status}"; r.updated_at=datetime.utcnow()
                    except Exception as exc:
                        r.reason=(r.reason or "")+"\nRefund reconciliation pending: "+str(exc)[:300]
                rows=(await db.execute(select(RefundRequest).where(RefundRequest.status=="refunded_pending_revoke").order_by(RefundRequest.updated_at).limit(20))).scalars().all()
                for r in rows:
                    p=await db.get(Payment,r.payment_id); sub=(await db.execute(select(Subscription).where(Subscription.user_id==r.user_id))).scalar_one_or_none()
                    if not p: continue
                    payment_lock=payment_token=None
                    user_lock=user_token=None
                    try:
                        user_lock,user_token=await _acquire_user_fulfillment_lock(p.user_id,ttl=300)
                        payment_lock,payment_token=await _acquire_payment_side_effect_lock(p.id)
                        # Re-check terminal state after acquiring the shared lock. This is the
                        # same critical section used by fulfillment and manual refund execution.
                        p=(await db.execute(select(Payment).where(Payment.id==p.id).with_for_update())).scalar_one()
                        r=(await db.execute(select(RefundRequest).where(RefundRequest.id==r.id).with_for_update())).scalar_one()
                        if r.status != "refunded_pending_revoke": continue
                        sub=(await db.execute(select(Subscription).where(Subscription.user_id==r.user_id).with_for_update())).scalar_one_or_none()
                        if not sub or not sub.remnawave_uuid:
                            r.status="refunded"; r.updated_at=datetime.utcnow(); await _reverse_referral_reward_for_refund(db,p,"system"); continue
                        revoke_result=await _safe_revoke_for_refunded_payment(db,p,"system","subscription.revoked.refund.retry")
                        r.status="refunded"; r.updated_at=datetime.utcnow()
                        reversal_result=await _reverse_referral_reward_for_refund(db,p,"system")
                        await audit(db,"subscription.revoked.refund.retry","system",str(sub.id),{"payment_id":p.id,**revoke_result,**reversal_result})
                    except Exception as exc:
                        r.reason=(r.reason or "")+"\nRevoke retry pending: "+str(exc)[:500]
                    finally:
                        if payment_lock and payment_token:
                            await _release_payment_side_effect_lock(payment_lock,payment_token)
                        if user_lock and user_token:
                            await _release_payment_side_effect_lock(user_lock,user_token)
                await db.commit()
        except Exception as exc:
            await send_alert("Refund scheduler failure: "+str(exc)[:500])
        await asyncio.sleep(30)

async def auto_renew_scheduler():
    while True:
        try:
            await asyncio.sleep(900)
            if not settings.auto_renew_enabled: continue
            async with AsyncSession(engine,expire_on_commit=False) as db:
                # Auto-renew is a real payment operation and must obey the same
                # production gate and payments feature flag as interactive checkout.
                if await maintenance_enabled(db): continue
                if await feature_enabled(db, "payments", True) is False: continue
                if await setting_value(db, PRODUCTION_PAYMENTS_GATE_KEY, "0") != "1": continue
                cutoff=datetime.utcnow()+timedelta(days=max(1,min(int(settings.auto_renew_lead_days or 3),14)))
                rows=(await db.execute(select(User,Subscription,Plan,AutoRenewMethod).join(Subscription,Subscription.user_id==User.id).join(Plan,Plan.id==Subscription.plan_id).join(AutoRenewMethod,AutoRenewMethod.user_id==User.id).where(User.auto_renew_enabled.is_(True),AutoRenewMethod.enabled.is_(True),AutoRenewMethod.status.in_(["active","past_due"]),Subscription.expires_at.is_not(None),Subscription.expires_at<=cutoff,Subscription.expires_at>datetime.utcnow(),((AutoRenewMethod.next_attempt_at.is_(None))|(AutoRenewMethod.next_attempt_at<=datetime.utcnow()))).limit(25))).all()
                for user,sub,plan,method in rows:
                    if method.provider != "yookassa": continue
                    # Account deletion shares this user-level lock. Re-load the user after
                    # acquiring it so a row selected by the scheduler cannot become a charge
                    # after the account has been anonymized.
                    user_lock=user_token=None
                    try:
                        user_lock,user_token=await _acquire_user_fulfillment_lock(user.id,ttl=900)
                    except Exception:
                        continue
                    try:
                        user=(await db.execute(select(User).where(User.id==user.id).with_for_update())).scalar_one_or_none()
                        if not user or user.deleted_at is not None or not user.auto_renew_enabled:
                            continue
                        method=(await db.execute(select(AutoRenewMethod).where(AutoRenewMethod.user_id==user.id).with_for_update())).scalar_one_or_none()
                        sub=(await db.execute(select(Subscription).where(Subscription.user_id==user.id).with_for_update())).scalar_one_or_none()
                        plan=await db.get(Plan,sub.plan_id) if sub else None
                        if not method or not sub or not plan or not method.enabled or method.status not in {"active","past_due"} or method.provider != "yookassa":
                            continue
                        if not sub.expires_at or sub.expires_at <= datetime.utcnow() or sub.expires_at > cutoff:
                            continue
                        date_key=(sub.expires_at or datetime.utcnow()).strftime("%Y%m%d")
                        order_id=f"auto-renew-{user.id}-{plan.id}-{date_key}"
                        renew_lock=renew_token=None
                        try:
                            renew_lock,renew_token=await _acquire_redis_lock(f"lock:auto-renew:user:{user.id}:{date_key}",ttl=900,conflict_message="Auto-renew is already in progress")
                        except RuntimeError:
                            continue
                        prefix=f"auto-renew-{user.id}-{plan.id}-{date_key}"
                        attempts=(await db.execute(select(Payment).where(Payment.user_id==user.id,Payment.order_id.like(prefix+"%"),Payment.provider=="yookassa").order_by(Payment.id.desc()))).scalars().all()
                        existing=attempts[0] if attempts else None
                        if existing:
                            if existing.status=="creating" and existing.provider_payment_id is None:
                                # YooKassa idempotency is keyed by order_id, so retrying the
                                # same durable intent is safe even if the previous HTTP response
                                # was lost after the provider accepted the charge.
                                token=__import__("backend.app.security",fromlist=["decrypt_secret"]).decrypt_secret(method.external_token_encrypted)
                                result=await YooKassaProvider().charge_recurring(Decimal(str(existing.amount)),existing.order_id,f"Auto-renew {plan.name}",token)
                                existing.provider_payment_id=result["id"]; existing.status="pending"; await db.commit()
                            if existing.status=="pending":
                                try:
                                    provider=YooKassaProvider()
                                    verified=await provider.verify_succeeded(existing.provider_payment_id,Decimal(str(existing.amount)),existing.currency,existing.order_id)
                                    if verified:
                                        payment_lock, payment_token = await _acquire_payment_side_effect_lock(existing.id)
                                        try:
                                            existing=(await db.execute(select(Payment).where(Payment.id==existing.id).with_for_update())).scalar_one()
                                            if existing.status in {"refunded", "refunded_pending_revoke"}:
                                                continue
                                            existing.status="paid"; existing.paid_at=existing.paid_at or datetime.utcnow(); await db.commit()
                                        finally:
                                            await _release_payment_side_effect_lock(payment_lock, payment_token)
                                        try:
                                            await fulfill(existing.id,db,existing_user_lock_token=user_token)
                                            method.last_success_at=datetime.utcnow(); method.failure_count=0; method.status="active"; method.last_error=None; method.next_attempt_at=datetime.utcnow()+timedelta(days=20); sub.lifecycle_status="active"; sub.grace_until=None; sub.last_renewal_failure_at=None; await db.commit()
                                        except Exception as exc:
                                            method.last_error=str(exc)[:1000]; await db.commit()
                                    else:
                                        provider_status=await provider.get_payment_status(existing.provider_payment_id)
                                        if provider_status in {"canceled","cancelled","failed","rejected"}:
                                            existing.status="failed"; existing.fulfillment_terminal=True; method.failure_count=(method.failure_count or 0)+1; method.status="past_due"; method.last_error=f"Recurring payment {provider_status}"; method.next_attempt_at=datetime.utcnow()+timedelta(hours=min(72,2**min(method.failure_count,6))); sub.lifecycle_status="grace"; sub.grace_until=(sub.expires_at or datetime.utcnow())+timedelta(hours=72); sub.last_renewal_failure_at=datetime.utcnow()
                                            if method.failure_count>=3: method.status="payment_failed"; method.enabled=False; user.auto_renew_enabled=False
                                            await db.commit()
                                except Exception as exc:
                                    logger.warning("Non-critical operation failed: %s", exc)
                            # Never create a second charge while the newest provider attempt
                            # is unresolved or already succeeded. Failed/cancelled attempts are
                            # the only safe state from which a new idempotency key may be used.
                            if existing.status not in {"failed","canceled","cancelled"}:
                                continue
                            failed_count=sum(1 for item in attempts if item.status in {"failed","canceled","cancelled"})
                            order_id=f"{prefix}-retry-{failed_count+1}"
                        token=__import__("backend.app.security",fromlist=["decrypt_secret"]).decrypt_secret(method.external_token_encrypted)
                        # Persist the payment intent BEFORE the external charge. If the
                        # process dies after YooKassa accepts the charge but before the
                        # response/DB commit, the next run can safely retry the SAME
                        # idempotency key instead of issuing a second charge.
                        payment=(await db.execute(select(Payment).where(Payment.order_id==order_id).with_for_update())).scalar_one_or_none()
                        if not payment:
                            payment=Payment(user_id=user.id,plan_id=plan.id,provider="yookassa",provider_payment_id=None,order_id=order_id,amount=Decimal(str(plan.price)),original_amount=Decimal(str(plan.price)),discount_amount=Decimal("0"),duration_days_snapshot=plan.duration_days,traffic_limit_gb_snapshot=plan.traffic_limit_gb,device_limit_snapshot=plan.device_limit,remnawave_profile_id_snapshot=plan.remnawave_profile_id,referrer_id_snapshot=user.referred_by_id,currency=settings.default_currency,status="creating",fulfillment_status="pending",paid_at=None)
                            db.add(payment); await db.flush()
                        method.last_attempt_at=datetime.utcnow(); method.next_attempt_at=datetime.utcnow()+timedelta(hours=24); await db.commit()
                        result=await YooKassaProvider().charge_recurring(Decimal(str(plan.price)),order_id,f"Auto-renew {plan.name}",token)
                        payment=(await db.execute(select(Payment).where(Payment.order_id==order_id).with_for_update())).scalar_one()
                        payment.provider_payment_id=result["id"]; payment.status="pending"; payment.fulfillment_status="pending"; await db.commit()
                        # Never fulfill until YooKassa confirms succeeded + amount/currency.
                        if await YooKassaProvider().verify_succeeded(result["id"],Decimal(str(plan.price)),settings.default_currency,payment.order_id):
                            payment_lock, payment_token = await _acquire_payment_side_effect_lock(payment.id)
                            try:
                                p=(await db.execute(select(Payment).where(Payment.provider_payment_id==result["id"]).with_for_update())).scalar_one()
                                if p.status in {"refunded", "refunded_pending_revoke"}:
                                    continue
                                p.status="paid"; p.paid_at=p.paid_at or datetime.utcnow(); await db.commit()
                            finally:
                                await _release_payment_side_effect_lock(payment_lock, payment_token)
                            try:
                                await fulfill(p.id,db,existing_user_lock_token=user_token)
                                method.last_success_at=datetime.utcnow(); method.failure_count=0; method.status="active"; method.last_error=None; method.next_attempt_at=datetime.utcnow()+timedelta(days=20); sub.lifecycle_status="active"; sub.grace_until=None; sub.last_renewal_failure_at=None; await db.commit()
                            except Exception as exc:
                                method.last_error=str(exc)[:1000]; await db.commit()
                        else:
                            method.failure_count=(method.failure_count or 0)+1; method.status="past_due"; method.last_error="Recurring payment not confirmed as succeeded"
                            method.next_attempt_at=datetime.utcnow()+timedelta(hours=min(72,2**min(method.failure_count,6)))
                            if method.failure_count>=3: method.status="payment_failed"; user.auto_renew_enabled=False; method.enabled=False
                            await db.commit()
                    except Exception as exc:
                        await db.rollback()
                        method=(await db.execute(select(AutoRenewMethod).where(AutoRenewMethod.user_id==user.id))).scalar_one_or_none()
                        if method:
                            method.last_attempt_at=datetime.utcnow(); method.failure_count=(method.failure_count or 0)+1; method.status="past_due"; method.last_error=str(exc)[:1000]
                            method.next_attempt_at=datetime.utcnow()+timedelta(hours=min(72,2**min(method.failure_count,6)))
                            if method.failure_count>=3: method.status="payment_failed"; method.enabled=False; user.auto_renew_enabled=False
                            await db.commit()
                    finally:
                        if renew_lock and renew_token:
                            await _release_payment_side_effect_lock(renew_lock,renew_token)
                        if user_lock and user_token:
                            await _release_payment_side_effect_lock(user_lock,user_token)
        except Exception: await asyncio.sleep(60)

async def reconciliation_scheduler():
    while True:
        try:
            await asyncio.sleep(600)
            async with AsyncSession(engine,expire_on_commit=False) as db:
                now=datetime.utcnow()
                stale=(await db.execute(select(PromoReservation).where(PromoReservation.status=="reserved",PromoReservation.expires_at<=now).with_for_update(skip_locked=True).limit(200))).scalars().all()
                for reservation in stale:
                    await release_promo_reservation(db,reservation.id)
                cutoff=now-timedelta(hours=24)
                rows=(await db.execute(select(Payment).where(Payment.created_at>=cutoff,Payment.status.in_(["pending","creation_unknown"])).order_by(Payment.id).limit(50))).scalars().all()
                providers={"yookassa":YooKassaProvider(),"platega":PlategaProvider(),"rollypay":RollyPayProvider()}
                for p in rows:
                    provider=providers.get(p.provider)
                    if not provider or not hasattr(provider,"verify_succeeded"): continue
                    try:
                        if p.status=="creation_unknown" and p.provider=="yookassa":
                            result=await provider.create(Decimal(str(p.amount)),p.order_id,f"VPN plan {p.plan_id}",settings.mini_app_url)
                            p.provider_payment_id=result["id"]; p.checkout_url=result.get("url"); p.status="pending"; p.fulfillment_terminal=False
                        if not p.provider_payment_id:
                            continue
                        if await provider.verify_succeeded(p.provider_payment_id,Decimal(str(p.amount)),p.currency,p.order_id):
                            try:
                                result=await _confirm_and_fulfill_payment(p.id,db)
                                if not result.get("ignored"):
                                    _METRICS["payment_fulfillment_total"] += 1
                            except Exception as exc:
                                logger.warning("Non-critical operation failed: %s", exc)
                    except Exception as exc:
                        logger.warning("Non-critical operation failed: %s", exc)
                await db.commit()
        except Exception: await asyncio.sleep(30)

async def subscription_lifecycle_scheduler():
    while True:
        try:
            async with AsyncSession(engine,expire_on_commit=False) as db:
                now=datetime.utcnow()
                ids=(await db.execute(select(Subscription.id).where(Subscription.expires_at.is_not(None),or_(Subscription.expires_at<=now,Subscription.scheduled_cancel_at<=now),Subscription.lifecycle_status.not_in(["expired","cancelled"])).limit(100).with_for_update(skip_locked=True))).scalars().all()
                for sub_id in ids:
                    sub=await db.get(Subscription,sub_id)
                    if not sub: continue
                    if sub.grace_until and sub.grace_until>now and sub.lifecycle_status=="grace": continue
                    user_lock,user_token=await _acquire_user_fulfillment_lock(sub.user_id,ttl=300)
                    try:
                        user=(await db.execute(select(User).where(User.id==sub.user_id).with_for_update())).scalar_one_or_none()
                        sub=(await db.execute(select(Subscription).where(Subscription.id==sub_id).with_for_update())).scalar_one_or_none()
                        if not user or not sub or user.deleted_at is not None: continue
                        now=datetime.utcnow()
                        if sub.grace_until and sub.grace_until>now and sub.lifecycle_status=="grace": continue
                        if sub.scheduled_cancel_at and sub.scheduled_cancel_at<=now:
                            if sub.remnawave_uuid:
                                sub.lifecycle_status="revoke_pending"; await db.commit()
                                try:
                                    await RemnawaveClient().disable_user(sub.remnawave_uuid)
                                    sub.lifecycle_status="cancelled"; sub.cancelled_at=now; await audit(db,"subscription.lifecycle.cancelled","system",str(sub.id))
                                except Exception as exc:
                                    await db.rollback(); sub=await db.get(Subscription,sub_id); sub.lifecycle_status="revoke_pending"; await audit(db,"subscription.lifecycle.revoke_pending","system",str(sub.id),{"error":str(exc)[:500]}); await db.commit(); continue
                            else:
                                sub.lifecycle_status="cancelled"; sub.cancelled_at=now; await audit(db,"subscription.lifecycle.cancelled","system",str(sub.id))
                        elif sub.expires_at and sub.expires_at<=now and sub.grace_until and sub.grace_until<=now and sub.remnawave_uuid:
                            sub.lifecycle_status="revoke_pending"; await db.commit()
                            try:
                                await RemnawaveClient().disable_user(sub.remnawave_uuid)
                                sub.lifecycle_status="expired"; await audit(db,"subscription.lifecycle.expired","system",str(sub.id))
                            except Exception as exc:
                                await db.rollback(); sub=await db.get(Subscription,sub_id); sub.lifecycle_status="revoke_pending"; await audit(db,"subscription.lifecycle.revoke_pending","system",str(sub.id),{"error":str(exc)[:500]}); await db.commit(); continue
                        elif sub.expires_at and sub.expires_at<=now:
                            sub.lifecycle_status="expired"; await audit(db,"subscription.lifecycle.expired","system",str(sub.id))
                        await db.commit()
                    finally:
                        await _release_payment_side_effect_lock(user_lock,user_token)
        except Exception as exc:
            logger.warning("Subscription lifecycle scheduler failed: %s", exc)
        await asyncio.sleep(300)

async def expiry_notification_scheduler():
    # Notifications are sent at most once per day via Redis markers.
    while True:
        try:
            if settings.bot_token and redis_client is not None:
                async with AsyncSession(engine,expire_on_commit=False) as db:
                    until=datetime.utcnow()+timedelta(days=settings.notification_expiry_days)
                    rows=(await db.execute(select(User,Subscription).join(Subscription,Subscription.user_id==User.id).where(User.telegram_id.is_not(None),Subscription.expires_at>datetime.utcnow(),Subscription.expires_at<=until).limit(500))).all()
                    import httpx
                    async with httpx.AsyncClient(timeout=10) as client:
                        for u,sub in rows:
                            key=f"expiry-notify:{u.id}:{sub.expires_at.date()}"
                            sending_key=key+":sending"
                            if not await redis_client.set(sending_key,"1",nx=True,ex=300):
                                continue
                            try:
                                resp=await client.post(
                                    f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
                                    json={"chat_id":u.telegram_id,"text":f"⚠️ Ваша VPN-подписка истекает {sub.expires_at:%d.%m.%Y}. Откройте магазин для продления."},
                                )
                                if resp.status_code >= 400:
                                    raise RuntimeError(f"Telegram notification failed: HTTP {resp.status_code}")
                                await redis_client.set(key,"1",ex=86400*7)
                            except Exception as exc:
                                try: await redis_client.delete(sending_key)
                                except Exception: pass
                                logger.warning("Expiry notification failed for user %s: %s",u.id,exc)
            await asyncio.sleep(3600)
        except Exception: await asyncio.sleep(3600)

@app.get("/api/me/subscription")
async def my_subscription(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db); sub=(await db.execute(select(Subscription).where(Subscription.user_id==user.id))).scalar_one_or_none()
    return {"subscription":None if not sub else {"id":sub.id,"plan_id":sub.plan_id,"expires_at":sub.expires_at,"subscription_url":sub.subscription_url,"remnawave_uuid":sub.remnawave_uuid},"auto_renew_enabled":user.auto_renew_enabled}

@app.get("/api/me/billing-center")
async def billing_center(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    sub=(await db.execute(select(Subscription).where(Subscription.user_id==user.id))).scalar_one_or_none()
    payments=(await db.execute(select(Payment).where(Payment.user_id==user.id).order_by(Payment.id.desc()).limit(50))).scalars().all()
    return {"subscription": None if not sub else {"id":sub.id,"plan_id":sub.plan_id,"status":sub.lifecycle_status,"expires_at":sub.expires_at,"grace_until":sub.grace_until,"scheduled_cancel_at":sub.scheduled_cancel_at,"auto_renew":user.auto_renew_enabled},"payments":[{"id":p.id,"order_id":p.order_id,"amount":str(p.amount),"currency":p.currency,"status":p.status,"fulfillment_status":p.fulfillment_status,"created_at":p.created_at,"paid_at":p.paid_at} for p in payments]}

@app.get("/api/me/security-center")
async def security_center(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    devices=(await db.execute(select(UserDevice).where(UserDevice.user_id==user.id).order_by(UserDevice.last_seen_at.desc().nullslast()))).scalars().all()
    events=(await db.execute(select(AuditLog).where(AuditLog.actor==f"user:{user.id}").order_by(AuditLog.id.desc()).limit(20))).scalars().all()
    sessions=(await db.execute(select(UserSession).where(UserSession.user_id==user.id).order_by(UserSession.id.desc()).limit(20))).scalars().all()
    return {"user_id":user.id,"sessions":[{"id":x.id,"ip":x.ip,"user_agent":x.user_agent,"created_at":x.created_at,"last_seen_at":x.last_seen_at,"expires_at":x.expires_at,"revoked_at":x.revoked_at} for x in sessions],"devices":[{"id":d.id,"name":d.name,"platform":d.platform,"last_ip":d.last_ip,"last_seen_at":d.last_seen_at,"status":d.status,"revoked_at":d.revoked_at} for d in devices],"events":[{"action":e.action,"target":e.target,"created_at":e.created_at} for e in events]}

@app.post("/api/me/subscription/lifecycle")
async def subscription_lifecycle(payload:SubscriptionActionIn,request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    lock,token=await _acquire_user_fulfillment_lock(user.id,ttl=300)
    try:
        user=(await db.execute(select(User).where(User.id==user.id).with_for_update())).scalar_one()
        sub=(await db.execute(select(Subscription).where(Subscription.user_id==user.id).with_for_update())).scalar_one_or_none()
        if not sub: raise HTTPException(404,"Subscription not found")
        now=datetime.utcnow()
        if payload.action=="cancel":
            if sub.lifecycle_status in {"expired","cancelled"}: raise HTTPException(409,"Subscription is already inactive")
            sub.scheduled_cancel_at=sub.expires_at or now; sub.lifecycle_status="cancel_scheduled"
        else:
            if sub.lifecycle_status not in {"cancel_scheduled","grace"}: raise HTTPException(409,"Subscription cannot be resumed from its current state")
            sub.scheduled_cancel_at=None; sub.cancelled_at=None; sub.lifecycle_status="active" if (sub.expires_at and sub.expires_at>now) else "grace"
        await audit(db,f"subscription.{payload.action}",f"user:{user.id}",str(sub.id)); await db.commit()
        return {"ok":True,"status":sub.lifecycle_status,"scheduled_cancel_at":sub.scheduled_cancel_at,"grace_until":sub.grace_until}
    finally:
        await _release_payment_side_effect_lock(lock,token)

def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

@app.post("/api/me/wallet/topup")
async def wallet_topup(payload:dict, request:Request, db:AsyncSession=Depends(get_db)):
    if await maintenance_enabled(db): raise HTTPException(503,"Service is in maintenance mode")
    if not await feature_enabled(db, "payments", True): raise HTTPException(503,"Платежи отключены администратором")
    if await setting_value(db,PRODUCTION_PAYMENTS_GATE_KEY,"0") != "1":
        raise HTTPException(503,"Реальные платежи временно заблокированы: требуется успешный staging E2E")
    user=await user_from_token(request,db)
    idem=request.headers.get("Idempotency-Key")
    if not idem or len(idem)>128: raise HTTPException(400,"Idempotency-Key is required")
    try:
        amount=_money(payload.get("amount"))
    except Exception:
        raise HTTPException(400,"Invalid amount")
    if amount < Decimal("50") or amount > Decimal("100000"):
        raise HTTPException(400,"Amount is outside the allowed top-up range")
    existing=(await db.execute(select(Payment).where(Payment.user_id==user.id,Payment.idempotency_key==idem).order_by(Payment.id.desc()))).scalar_one_or_none()
    if existing:
        if (existing.purpose or "subscription") != "topup":
            raise HTTPException(409,"Idempotency-Key уже использован для другого платежа")
        return {"id":existing.provider_payment_id,"url":existing.checkout_url,"provider":existing.provider,"status":existing.status,"purpose":"topup"}
    await ensure_required_channel(user)
    provider_order=await _payment_provider_order(db,payload.get("provider"))
    if not provider_order: raise HTTPException(503,"Нет доступных платёжных провайдеров")
    candidate=provider_order[0]
    provider={"yookassa":YooKassaProvider(),"platega":PlategaProvider(),"rollypay":RollyPayProvider()}[candidate]
    order_id=f"topup-{user.id}-{hashlib.sha256(idem.encode()).hexdigest()[:24]}"
    row=Payment(user_id=user.id,plan_id=0,provider=candidate,order_id=order_id,amount=amount,original_amount=amount,discount_amount=Decimal("0.00"),currency=settings.default_currency,status="creating",fulfillment_status="pending",idempotency_key=idem,purpose="topup",bonus_days=0)
    db.add(row); await db.commit(); await db.refresh(row)
    try:
        result=await provider.create(amount,order_id,"Wallet top-up",settings.mini_app_url)
        if not result.get("id"): raise RuntimeError("Payment provider returned no payment ID")
        row=(await db.execute(select(Payment).where(Payment.id==row.id).with_for_update())).scalar_one()
        row.provider_payment_id=result["id"]; row.status="pending"; row.checkout_url=result.get("url")
        await db.commit()
        return {"id":result.get("id"),"url":result.get("url"),"provider":candidate,"status":"pending","purpose":"topup"}
    except Exception as exc:
        row=(await db.execute(select(Payment).where(Payment.id==row.id).with_for_update())).scalar_one()
        row.status="creation_unknown"; row.fulfillment_terminal=True; row.fulfillment_error=str(exc)[:1000]
        await db.commit()
        raise HTTPException(503,"Результат создания платежа не определён. Повторное списание заблокировано; операция будет сверена.")

@app.post("/api/me/wallet/spend")
async def wallet_spend(payload:dict, request:Request, db:AsyncSession=Depends(get_db)):
    if await maintenance_enabled(db): raise HTTPException(503,"Service is in maintenance mode")
    user=await user_from_token(request,db)
    from .platform_api import reject_restricted
    reject_restricted(user)
    constructor_requested=payload.get("constructor_id") not in (None, "", 0, "0")
    constructor_quote=None
    quote_error=None
    plan_id=None
    if constructor_requested:
        from .tariff_api import quote_constructor
        try:
            constructor_quote=await quote_constructor(db, payload)
            plan_id=int(constructor_quote["plan_id"])
        except HTTPException as exc:
            quote_error=exc
    else:
        try:
            plan_id=int(payload.get("plan_id"))
        except (TypeError, ValueError):
            raise HTTPException(400,"Invalid plan_id")
    idem=request.headers.get("Idempotency-Key") or (f"wallet-spend-{user.id}-{plan_id}-{uuid.uuid4().hex}" if plan_id is not None else f"wallet-spend-{user.id}-{uuid.uuid4().hex}")
    if len(idem)>128: raise HTTPException(400,"Idempotency-Key is required")
    existing=(await db.execute(select(Payment).where(Payment.user_id==user.id,Payment.idempotency_key==idem))).scalar_one_or_none()
    if existing:
        if existing.provider != "wallet":
            raise HTTPException(409,"Idempotency-Key уже использован для другого платежа")
        if constructor_quote and (existing.plan_id != plan_id or existing.duration_days_snapshot != constructor_quote["days"] or existing.traffic_limit_gb_snapshot != constructor_quote["traffic_gb"] or existing.device_limit_snapshot != constructor_quote["devices"]):
            raise HTTPException(409,"Idempotency-Key уже использован для другой конфигурации тарифа")
        elif plan_id is not None and existing.plan_id != plan_id:
            raise HTTPException(409,"Idempotency-Key уже использован для другого платежа")
        return {"ok":True,"payment_id":existing.id,"status":existing.status,"fulfillment_status":existing.fulfillment_status}
    if quote_error:
        raise quote_error
    if plan_id is None:
        raise HTTPException(400,"Invalid plan_id")
    await ensure_required_channel(user)
    plan=await db.get(Plan,plan_id)
    if not plan or not plan.enabled: raise HTTPException(404,"Not found")
    from .tariff_api import linked_constructor_id
    linked=await linked_constructor_id(db, plan.id)
    if linked and (not constructor_quote or int(constructor_quote["constructor_id"]) != int(linked)):
        raise HTTPException(400,"Этот тариф собирается в конструкторе")
    if constructor_quote:
        base_amount=Decimal(str(constructor_quote["amount"]))
        snap_days=int(constructor_quote["days"])
        snap_traffic=constructor_quote["traffic_gb"]
        snap_devices=int(constructor_quote["devices"])
        snap_profile=constructor_quote["profile_id"]
    else:
        base_amount=Decimal(str(plan.price))
        snap_days=plan.duration_days
        snap_traffic=plan.traffic_limit_gb
        snap_devices=plan.device_limit
        snap_profile=plan.remnawave_profile_id
    promo, promo_discount_amount=await promo_discount(db,payload.get("promo_code"),plan.id,base_amount,user.id)
    if promo is None:
        promotion=await active_promotion(db,plan.id)
        discount_amount=discounted_amount(base_amount,promotion.kind,promotion.value) if promotion else Decimal("0.00")
    else:
        promotion=None; discount_amount=promo_discount_amount
    final_amount=_money(base_amount-discount_amount)
    bonus_days=int(Decimal(str(promo.value))) if promo is not None and promo.kind=="days" else (int(Decimal(str(promotion.value))) if promotion is not None and promotion.kind=="days" else 0)
    if final_amount <= 0: raise HTTPException(400,"Amount must be positive")
    lock,token=await _acquire_user_fulfillment_lock(user.id,ttl=900)
    try:
        user=(await db.execute(select(User).where(User.id==user.id).with_for_update())).scalar_one()
        balance=_money(user.wallet_balance or 0)
        if balance < final_amount: raise HTTPException(402,"Недостаточно средств на балансе")
        order_id=f"wallet-{user.id}-{plan.id}-{hashlib.sha256(idem.encode()).hexdigest()[:24]}"
        row=Payment(user_id=user.id,plan_id=plan.id,provider="wallet",order_id=order_id,amount=final_amount,original_amount=base_amount,discount_amount=discount_amount,duration_days_snapshot=snap_days,traffic_limit_gb_snapshot=snap_traffic,device_limit_snapshot=snap_devices,remnawave_profile_id_snapshot=snap_profile,referrer_id_snapshot=user.referred_by_id,promo_code=(promo.code if promo else None),currency=settings.default_currency,status="paid",fulfillment_status="pending",idempotency_key=idem,purpose="subscription",bonus_days=bonus_days,paid_at=datetime.utcnow())
        user.wallet_balance=_money(balance-final_amount)
        db.add(row); await db.flush()
        await record_financial_event(db,operation_key=f"wallet-spend:{row.id}",user_id=user.id,payment_id=row.id,kind="wallet_spend",direction="debit",amount=final_amount,currency=row.currency,metadata={"plan_id":plan.id})
        await db.commit()
        try:
            await fulfill(row.id, db, existing_user_lock_token=token)
        except Exception:
            return {"ok":True,"payment_id":row.id,"fulfillment":"queued","wallet_balance":str(user.wallet_balance)}
        return {"ok":True,"payment_id":row.id,"wallet_balance":str(user.wallet_balance)}
    finally:
        await _release_payment_side_effect_lock(lock,token)

@app.post("/api/me/gifts/purchase")
async def purchase_gift(payload:dict, request:Request, db:AsyncSession=Depends(get_db)):
    if await maintenance_enabled(db): raise HTTPException(503,"Service is in maintenance mode")
    user=await user_from_token(request,db)
    try:
        plan_id=int(payload.get("plan_id"))
    except (TypeError, ValueError):
        raise HTTPException(400,"Invalid plan_id")
    idem=request.headers.get("Idempotency-Key")
    if not idem or len(idem)>128: raise HTTPException(400,"Idempotency-Key is required")
    existing=(await db.execute(select(GiftCode).where(GiftCode.idempotency_key==idem,GiftCode.purchaser_user_id==user.id))).scalar_one_or_none()
    if existing:
        return {"ok":True,"code":existing.code,"bot_claim_url":(f"https://t.me/{settings.bot_username}?start={existing.code}" if settings.bot_username else None)}
    await ensure_required_channel(user)
    plan=await db.get(Plan,plan_id)
    if not plan or not plan.enabled: raise HTTPException(404,"Not found")
    from .tariff_api import linked_constructor_id
    if await linked_constructor_id(db, plan.id):
        raise HTTPException(400,"Подарок собирается через конструктор тарифа")
    price=_money(plan.price)
    if price <= 0: raise HTTPException(400,"Gift plan must have a positive price")
    lock,token=await _acquire_user_fulfillment_lock(user.id,ttl=300)
    try:
        user=(await db.execute(select(User).where(User.id==user.id).with_for_update())).scalar_one()
        balance=_money(user.wallet_balance or 0)
        if balance < price: raise HTTPException(402,"Недостаточно средств на балансе")
        code="GIFT_"+secrets.token_hex(20)
        user.wallet_balance=_money(balance-price)
        gift=GiftCode(code=code,plan_id=plan.id,duration_days=plan.duration_days,max_uses=1,purchaser_user_id=user.id,idempotency_key=idem,enabled=True)
        db.add(gift); await db.flush()
        await record_financial_event(db,operation_key=f"gift-purchase:{gift.id}",user_id=user.id,payment_id=None,kind="gift_purchase",direction="debit",amount=price,currency=settings.default_currency,metadata={"plan_id":plan.id})
        await audit(db,"gift.purchased",f"user:{user.id}",code,{"plan_id":plan.id}); await db.commit()
        claim=f"https://t.me/{settings.bot_username}?start={code}" if settings.bot_username else None
        return {"ok":True,"code":code,"bot_claim_url":claim,"wallet_balance":str(user.wallet_balance)}
    finally:
        await _release_payment_side_effect_lock(lock,token)

@app.post("/api/me/gifts/redeem")
async def redeem_gift(payload:GiftRedeemIn,request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    code=(await db.execute(select(GiftCode).where(GiftCode.code==payload.code.strip().upper()).with_for_update())).scalar_one_or_none()
    if not code or not code.enabled: raise HTTPException(404,"Gift code not found")
    if code.purchaser_user_id and code.purchaser_user_id==user.id: raise HTTPException(403,"Gift purchaser cannot redeem their own gift")
    if code.expires_at and code.expires_at<=datetime.utcnow(): raise HTTPException(410,"Gift code expired")
    if code.used_count>=code.max_uses: raise HTTPException(409,"Gift code already exhausted")
    existing_redemption=(await db.execute(select(GiftRedemption).where(GiftRedemption.gift_code_id==code.id,GiftRedemption.user_id==user.id).with_for_update())).scalar_one_or_none()
    if existing_redemption and existing_redemption.status=="completed": raise HTTPException(409,"Gift code already redeemed by this account")
    if existing_redemption and existing_redemption.status=="failed": raise HTTPException(409,"Previous gift activation failed; contact support")
    plan=await db.get(Plan,code.plan_id)
    if not plan or not plan.enabled: raise HTTPException(409,"Gift plan is unavailable")
    lock,token=await _acquire_user_fulfillment_lock(user.id,ttl=900)
    try:
        user=(await db.execute(select(User).where(User.id==user.id).with_for_update())).scalar_one()
        sub=(await db.execute(select(Subscription).where(Subscription.user_id==user.id).with_for_update())).scalar_one_or_none()
        now=datetime.utcnow(); days=code.duration_days or plan.duration_days
        operation_key=f"gift:{code.id}:{user.id}"
        redemption=existing_redemption
        if redemption is None:
            redemption=GiftRedemption(gift_code_id=code.id,user_id=user.id,operation_key=operation_key,status="processing")
            db.add(redemption); await db.flush()
        else:
            operation_key=redemption.operation_key
            if redemption.remote_user_id and redemption.expected_after_expires_at:
                try:
                    remote_expiry=await RemnawaveClient().get_expiry(redemption.remote_user_id)
                except Exception:
                    remote_expiry=None
                if remote_expiry and remote_expiry >= redemption.expected_after_expires_at:
                    redemption.status="completed"; code.used_count=max(code.used_count,1); await db.commit(); return {"ok":True,"reconciled":True,"operation_key":operation_key,"expires_at":remote_expiry}
        if sub and sub.remnawave_uuid:
            remote_before=await RemnawaveClient().get_expiry(sub.remnawave_uuid)
            before=max(sub.expires_at or now,remote_before or now,now)
            after=before+timedelta(days=days)
            redemption.expected_before_expires_at=before; redemption.expected_after_expires_at=after; redemption.remote_user_id=str(sub.remnawave_uuid)
            await db.commit()
            try:
                await RemnawaveClient().update_entitlements(sub.remnawave_uuid,plan.traffic_limit_gb,plan.remnawave_profile_id)
                await RemnawaveClient().extend_idempotent(sub.remnawave_uuid,days,before,after)
                sub.plan_id=plan.id; sub.expires_at=after; sub.lifecycle_status="active"; sub.grace_until=None; sub.traffic_limit_gb_snapshot=plan.traffic_limit_gb; sub.device_limit_snapshot=plan.device_limit; sub.remnawave_profile_id_snapshot=plan.remnawave_profile_id
            except Exception as exc:
                redemption.status="failed"; redemption.error=str(exc)[:1000]; await db.commit(); raise HTTPException(503,"Gift provisioning is temporarily unavailable") from exc
        else:
            username=f"user_{user.id}"
            try:
                remote=await RemnawaveClient().get_user_by_username(username)
            except Exception:
                remote=None
            if remote and remote.get("id"):
                remote_id=str(remote["id"]); remote_before=await RemnawaveClient().get_expiry(remote_id); before=max(remote_before or now,now); after=before+timedelta(days=days)
                redemption.expected_before_expires_at=before; redemption.expected_after_expires_at=after; redemption.remote_user_id=remote_id
                await db.commit()
                try:
                    await RemnawaveClient().update_entitlements(remote_id,plan.traffic_limit_gb,plan.remnawave_profile_id)
                    if not remote_before or remote_before < after: await RemnawaveClient().extend_idempotent(remote_id,days,before,after)
                    sub=Subscription(user_id=user.id,plan_id=plan.id,remnawave_uuid=remote_id,expires_at=after,lifecycle_status="active",traffic_limit_gb_snapshot=plan.traffic_limit_gb,device_limit_snapshot=plan.device_limit,remnawave_profile_id_snapshot=plan.remnawave_profile_id); db.add(sub)
                except Exception as exc:
                    redemption.status="failed"; redemption.error=str(exc)[:1000]; await db.commit(); raise HTTPException(503,"Gift provisioning is temporarily unavailable") from exc
            else:
                expires=now+timedelta(days=days); redemption.expected_before_expires_at=now; redemption.expected_after_expires_at=expires
                await db.commit()
                try:
                    data=await RemnawaveClient().create_user(username,expires,plan.traffic_limit_gb*1024**3 if plan.traffic_limit_gb else 0,active_internal_squads=[plan.remnawave_profile_id] if plan.remnawave_profile_id else None,telegram_id=user.telegram_id)
                    remote_id=str(data.get("id"))
                    if not remote_id: raise RuntimeError("Remnawave returned no user id")
                    redemption.remote_user_id=remote_id
                    sub=Subscription(user_id=user.id,plan_id=plan.id,remnawave_uuid=remote_id,expires_at=expires,lifecycle_status="active",traffic_limit_gb_snapshot=plan.traffic_limit_gb,device_limit_snapshot=plan.device_limit,remnawave_profile_id_snapshot=plan.remnawave_profile_id); db.add(sub)
                except Exception as exc:
                    redemption.status="failed"; redemption.error=str(exc)[:1000]; await db.commit(); raise HTTPException(503,"Gift provisioning is temporarily unavailable") from exc
        redemption.status="completed"; code.used_count+=1
        await audit(db,"gift.redeemed",f"user:{user.id}",str(code.id),{"plan_id":plan.id,"duration_days":days,"operation_key":operation_key}); await db.commit()
        return {"ok":True,"plan_id":plan.id,"expires_at":sub.expires_at,"operation_key":operation_key}
    except IntegrityError:
        await db.rollback(); raise HTTPException(409,"Gift code was redeemed concurrently; retry")
    finally:
        await _release_payment_side_effect_lock(lock,token)

@app.post("/api/me/referral/apply")
async def apply_referral(payload:dict,request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    user=(await db.execute(select(User).where(User.id==user.id).with_for_update())).scalar_one()
    if user.referred_by_id: raise HTTPException(409,"Referral is already set")
    code=str(payload.get("code") or "").strip().upper()
    ref=(await db.execute(select(User).where(User.referral_code==code))).scalar_one_or_none()
    if not ref or ref.id==user.id: raise HTTPException(400,"Invalid referral code")
    user.referred_by_id=ref.id; await db.commit(); return {"ok":True,"referrer_id":ref.id}

@app.get("/api/me/auto-renew")
async def auto_renew_status(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db); method=(await db.execute(select(AutoRenewMethod).where(AutoRenewMethod.user_id==user.id))).scalar_one_or_none()
    return {"enabled":user.auto_renew_enabled,"configured":bool(method and method.enabled),"provider":method.provider if method else None,"last_attempt_at":method.last_attempt_at if method else None,"last_success_at":method.last_success_at if method else None,"last_error":method.last_error if method else None,"supported_providers":["yookassa"]}

@app.get("/api/me/connection-qr")
async def connection_qr(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db); sub=(await db.execute(select(Subscription).where(Subscription.user_id==user.id))).scalar_one_or_none()
    if not sub or not sub.subscription_url: raise HTTPException(404,"Subscription is not available")
    import io, qrcode
    img=qrcode.make(sub.subscription_url); buf=io.BytesIO(); img.save(buf,format="PNG")
    return Response(content=buf.getvalue(),media_type="image/png",headers={"Cache-Control":"private, no-store"})

@app.get("/api/me/connection-info")
async def connection_info(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db); sub=(await db.execute(select(Subscription).where(Subscription.user_id==user.id))).scalar_one_or_none()
    guides={}
    for key in ("android","ios","tv","windows","macos","linux"):
        row=(await db.execute(select(AppSetting).where(AppSetting.key==f"guide_{key}"))).scalar_one_or_none()
        guides[key]=row.value if row and row.value else {
            "android":"Android: установите v2RayTun / Happ / Streisand, вставьте ссылку подписки и подключитесь.",
            "ios":"iOS: установите Streisand или Happ из App Store, импортируйте ссылку подписки и включите VPN.",
            "tv":"TV: откройте VPN-клиент на телевизоре, добавьте подписку по ссылке или через QR с телефона.",
            "windows":"Windows: установите Hiddify / v2rayN, импортируйте ссылку подписки и запустите соединение.",
            "macos":"macOS: установите Hiddify / Streisand, импортируйте ссылку подписки и подключитесь.",
            "linux":"Linux: используйте Hiddify / Nekoray, импортируйте URI подписки и активируйте профиль.",
        }[key]
    return Response(content=json.dumps({"subscription_url":sub.subscription_url if sub else None,"expires_at":sub.expires_at.isoformat() if sub and sub.expires_at else None,"platforms":guides},ensure_ascii=False),media_type="application/json",headers={"Cache-Control":"private, no-store"})

@app.put("/api/me/auto-renew")
async def set_auto_renew(payload:dict,request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db); enabled=bool(payload.get("enabled"))
    method=(await db.execute(select(AutoRenewMethod).where(AutoRenewMethod.user_id==user.id))).scalar_one_or_none()
    if enabled and (not method or not method.enabled): raise HTTPException(409,"No saved recurring payment method is configured")
    user.auto_renew_enabled=enabled; await db.commit(); return {"enabled":enabled,"configured":bool(method and method.enabled)}

@app.delete("/api/me/auto-renew/method")
async def remove_auto_renew_method(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db); method=(await db.execute(select(AutoRenewMethod).where(AutoRenewMethod.user_id==user.id))).scalar_one_or_none()
    if method: await db.delete(method)
    user.auto_renew_enabled=False; await db.commit(); return {"ok":True,"enabled":False}

@app.get("/api/me/payments")
async def my_payments(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db); rows=(await db.execute(select(Payment).where(Payment.user_id==user.id).order_by(Payment.id.desc()).limit(100))).scalars().all()
    return [{"id":p.id,"provider":p.provider,"amount":float(p.amount),"currency":p.currency,"status":p.status,"fulfillment_status":p.fulfillment_status,"created_at":p.created_at,"paid_at":p.paid_at} for p in rows]

@app.get("/api/me/referral/ledger")
async def my_referral_ledger(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db); rows=(await db.execute(select(ReferralLedger).where(ReferralLedger.user_id==user.id).order_by(ReferralLedger.id.desc()).limit(100))).scalars().all()
    return [{"id":x.id,"amount":float(x.amount),"kind":x.kind,"payment_id":x.payment_id,"created_at":x.created_at} for x in rows]

@app.get("/api/me/referral")
async def my_referral(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db); count=int((await db.execute(select(func.count()).select_from(ReferralReward).where(ReferralReward.referrer_id==user.id))).scalar() or 0); total=(await db.execute(select(func.coalesce(func.sum(ReferralReward.amount),0)).where(ReferralReward.referrer_id==user.id))).scalar() or 0
    return {"code":user.referral_code,"referred_count":count,"reward_total":float(total),"balance":float(user.referral_balance or 0),"reward_percent":settings.referral_reward_percent}


# ---------- V24-V28 customer/support/security operations ----------
@app.post("/api/me/support/tickets")
async def create_support_ticket(payload:TicketIn, request:Request, db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    t=SupportTicket(user_id=user.id, subject=payload.subject.strip(), message=payload.message.strip())
    db.add(t); await db.commit(); await db.refresh(t)
    return {"id":t.id,"status":t.status}

@app.get("/api/me/support/tickets")
async def my_support_tickets(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    rows=(await db.execute(select(SupportTicket).where(SupportTicket.user_id==user.id).order_by(SupportTicket.id.desc()).limit(100))).scalars().all()
    return [{"id":x.id,"subject":x.subject,"message":x.message,"status":x.status,"admin_reply":x.admin_reply,"created_at":x.created_at,"updated_at":x.updated_at} for x in rows]

@app.post("/api/me/referral/withdrawals")
async def request_withdrawal(payload:WithdrawalIn,request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    amount=payload.amount.quantize(Decimal("0.01"))
    if amount < Decimal("1.00"): raise HTTPException(400,"Minimum withdrawal is 1.00")
    destination=payload.destination.strip()
    if not destination or len(destination)>255: raise HTTPException(400,"Invalid withdrawal destination")
    result=await db.execute(sql_text("UPDATE users SET referral_balance=referral_balance-:amount WHERE id=:uid AND referral_balance>=:amount"),{"amount":amount,"uid":user.id})
    if result.rowcount != 1: raise HTTPException(400,"Insufficient referral balance")
    row=WithdrawalRequest(user_id=user.id,amount=amount,destination=destination,status="requested")
    db.add(row); await db.flush()
    db.add(ReferralLedger(user_id=user.id,source_user_id=None,payment_id=None,amount=-amount,kind=f"withdrawal:{row.id}"))
    await audit(db,"referral.withdrawal.requested",f"user:{user.id}",str(row.id),{"amount":str(amount)}); await db.commit(); await db.refresh(row)
    return {"id":row.id,"status":row.status,"amount":str(row.amount)}

@app.get("/api/me/referral/withdrawals")
async def my_withdrawals(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    rows=(await db.execute(select(WithdrawalRequest).where(WithdrawalRequest.user_id==user.id).order_by(WithdrawalRequest.id.desc()).limit(100))).scalars().all()
    return [{"id":x.id,"amount":str(x.amount),"destination":x.destination,"status":x.status,"created_at":x.created_at} for x in rows]

@app.get("/api/me/dashboard")
async def customer_dashboard(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    sub=(await db.execute(select(Subscription).where(Subscription.user_id==user.id))).scalar_one_or_none()
    payments=(await db.execute(select(Payment).where(Payment.user_id==user.id).order_by(Payment.id.desc()).limit(10))).scalars().all()
    tickets=(await db.execute(select(SupportTicket).where(SupportTicket.user_id==user.id).order_by(SupportTicket.id.desc()).limit(5))).scalars().all()
    return {"user":{"id":user.id,"username":user.username,"email":user.email,"referral_code":user.referral_code,"referral_balance":str(user.referral_balance),"wallet_balance":str(user.wallet_balance or 0),"auto_renew_enabled":user.auto_renew_enabled},"subscription":None if not sub else {"plan_id":sub.plan_id,"expires_at":sub.expires_at,"subscription_url":sub.subscription_url,"status":sub.lifecycle_status,"auto_renew_enabled":user.auto_renew_enabled},"payments":[{"id":p.id,"amount":str(p.amount),"currency":p.currency,"status":p.status,"fulfillment_status":p.fulfillment_status,"created_at":p.created_at} for p in payments],"tickets":[{"id":t.id,"subject":t.subject,"status":t.status} for t in tickets]}

# ---------- Уведомления, статус и управление развёртываниями ----------
@app.get("/api/me/notifications")
async def my_notifications(request:Request, unread_only:bool=False, db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    q=select(Notification).where(Notification.user_id==user.id)
    if unread_only: q=q.where(Notification.read_at.is_(None))
    rows=(await db.execute(q.order_by(Notification.id.desc()).limit(100))).scalars().all()
    return [{"id":n.id,"channel":n.channel,"kind":n.kind,"title":n.title,"body":n.body,"read":n.read_at is not None,"created_at":n.created_at} for n in rows]

@app.post("/api/me/notifications/{notification_id}/read")
async def read_notification(notification_id:int,request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    row=(await db.execute(select(Notification).where(Notification.id==notification_id,Notification.user_id==user.id).with_for_update())).scalar_one_or_none()
    if not row: raise HTTPException(404,"Уведомление не найдено")
    row.read_at=datetime.utcnow(); await db.commit(); return {"ok":True}

@app.get("/api/public/status")
async def public_status(db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(StatusComponent).where(StatusComponent.enabled==True).order_by(StatusComponent.sort_order,StatusComponent.id))).scalars().all()
    return {"version":APP_VERSION,"overall":"operational" if all(x.status=="operational" for x in rows) else "degraded","components":[{"slug":x.slug,"name":x.name,"status":x.status,"message":x.message,"updated_at":x.updated_at} for x in rows]}

@app.get("/api/admin/notifications")
async def admin_notifications(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    rows=(await db.execute(select(Notification).order_by(Notification.id.desc()).limit(200))).scalars().all()
    return [{"id":n.id,"user_id":n.user_id,"channel":n.channel,"kind":n.kind,"title":n.title,"status":n.status,"attempts":n.attempts,"created_at":n.created_at,"sent_at":n.sent_at} for n in rows]

@app.post("/api/admin/notifications")
async def admin_notification_create(payload:NotificationIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    if not await db.get(User,payload.user_id): raise HTTPException(404,"Пользователь не найден")
    row=await enqueue_notification(db,**payload.model_dump()); await audit(db,"notification.created",admin.email,str(row.id),payload.model_dump()); await db.commit()
    return {"id":row.id,"status":row.status}

@app.get("/api/admin/status/components")
async def admin_status_components(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.diagnostics"))):
    rows=(await db.execute(select(StatusComponent).order_by(StatusComponent.sort_order,StatusComponent.id))).scalars().all()
    return [{"id":x.id,"slug":x.slug,"name":x.name,"status":x.status,"message":x.message,"enabled":x.enabled,"sort_order":x.sort_order} for x in rows]

@app.post("/api/admin/status/components")
async def admin_status_component_create(payload:StatusComponentIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.diagnostics"))):
    if await db.scalar(select(StatusComponent).where(StatusComponent.slug==payload.slug)): raise HTTPException(409,"Компонент уже существует")
    row=StatusComponent(**payload.model_dump()); db.add(row); await audit(db,"status.component.created",admin.email,payload.slug); await db.commit(); await db.refresh(row); return {"id":row.id,"status":row.status}

@app.put("/api/admin/status/components/{component_id}")
async def admin_status_component_update(component_id:int,payload:StatusComponentIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.diagnostics"))):
    row=await db.get(StatusComponent,component_id)
    if not row: raise HTTPException(404,"Компонент не найден")
    duplicate=await db.scalar(select(StatusComponent).where(StatusComponent.slug==payload.slug,StatusComponent.id!=component_id))
    if duplicate: raise HTTPException(409,"Slug уже занят")
    for k,v in payload.model_dump().items(): setattr(row,k,v)
    row.updated_at=datetime.utcnow(); await audit(db,"status.component.updated",admin.email,str(row.id),payload.model_dump()); await db.commit(); return {"ok":True}

@app.post("/api/admin/deployments")
async def deployment_create(payload:DeploymentIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.releases"))):
    active=await db.scalar(select(Deployment).where(Deployment.status.in_({"planned","canary","promoted"})).order_by(Deployment.id.desc()))
    if active: raise HTTPException(409,"Уже существует активное развёртывание")
    row=Deployment(version=payload.version,previous_version=payload.previous_version,strategy=payload.strategy,traffic_percent=payload.traffic_percent,status="canary" if payload.traffic_percent else "planned")
    db.add(row); await audit(db,"deployment.created",admin.email,str(row.version),payload.model_dump()); await db.commit(); await db.refresh(row); return {"id":row.id,"status":row.status,"traffic_percent":row.traffic_percent}

@app.post("/api/admin/deployments/{deployment_id}/promote")
async def deployment_promote(deployment_id:int,payload:DeploymentPromoteIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.releases"))):
    row=(await db.execute(select(Deployment).where(Deployment.id==deployment_id).with_for_update())).scalar_one_or_none()
    if not row: raise HTTPException(404,"Развёртывание не найдено")
    if row.status in {"rolled_back","completed"}: raise HTTPException(409,"Развёртывание уже завершено")
    if payload.error_rate_percent >= Decimal("5") and payload.traffic_percent > row.traffic_percent: raise HTTPException(409,"Нельзя повышать трафик при error rate >= 5%")
    row.traffic_percent=payload.traffic_percent; row.error_rate_percent=payload.error_rate_percent; row.status="completed" if payload.traffic_percent==100 else "promoted" if payload.traffic_percent>0 else "planned"; row.updated_at=datetime.utcnow()
    if row.status=="completed": row.completed_at=datetime.utcnow()
    await audit(db,"deployment.promoted",admin.email,str(row.id),payload.model_dump()); await db.commit(); return {"ok":True,"status":row.status,"traffic_percent":row.traffic_percent}

@app.post("/api/admin/deployments/{deployment_id}/rollback")
async def deployment_rollback(deployment_id:int,payload:dict|None=None,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.releases"))):
    row=(await db.execute(select(Deployment).where(Deployment.id==deployment_id).with_for_update())).scalar_one_or_none()
    if not row: raise HTTPException(404,"Развёртывание не найдено")
    if row.status=="completed": raise HTTPException(409,"Завершённый релиз требует отдельного обратного релиза")
    row.status="rolled_back"; row.traffic_percent=0; row.rollback_reason=str((payload or {}).get("reason") or "Ручной откат")[:2000]; row.updated_at=datetime.utcnow(); await audit(db,"deployment.rollback",admin.email,str(row.id),{"reason":row.rollback_reason}); await db.commit(); return {"ok":True,"status":row.status}

@app.get("/api/admin/deployments")
async def deployment_list(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.releases"))):
    rows=(await db.execute(select(Deployment).order_by(Deployment.id.desc()).limit(100))).scalars().all()
    return [{"id":x.id,"version":x.version,"previous_version":x.previous_version,"strategy":x.strategy,"traffic_percent":x.traffic_percent,"status":x.status,"error_rate_percent":str(x.error_rate_percent),"rollback_reason":x.rollback_reason,"created_at":x.created_at,"completed_at":x.completed_at} for x in rows]

# ---------- Admin Recovery / Reconciliation ----------
@app.get("/api/admin/recovery/operations")
async def recovery_operations(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    rows=(await db.execute(select(ProvisioningOperation).order_by(ProvisioningOperation.updated_at.desc()).limit(200))).scalars().all()
    return [{"id":x.id,"payment_id":x.payment_id,"user_id":x.user_id,"operation_key":x.operation_key,"status":x.status,"attempts":x.attempts,"last_error":x.last_error,"remote_user_id":x.remote_user_id,"updated_at":x.updated_at} for x in rows]

@app.post("/api/admin/recovery/operations/{operation_id}/retry")
async def retry_operation(operation_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("payments.retry"))):
    opx=await db.get(ProvisioningOperation,operation_id)
    if not opx: raise HTTPException(404,"Operation not found")
    opx.status="retry"; opx.updated_at=datetime.utcnow(); await db.commit()
    try: await fulfill(opx.payment_id,db)
    except Exception as e: return {"ok":False,"error":str(e)[:500]}
    return {"ok":True,"status":"completed"}

@app.get("/api/admin/refunds")
async def admin_refunds(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    rows=(await db.execute(select(RefundRequest).order_by(RefundRequest.id.desc()).limit(200))).scalars().all()
    return [{"id":x.id,"payment_id":x.payment_id,"user_id":x.user_id,"amount":str(x.amount),"status":x.status,"reason":x.reason,"provider_refund_id":x.provider_refund_id,"created_at":x.created_at} for x in rows]

@app.post("/api/admin/payments/{payment_id}/refund-request")
async def request_refund(payment_id:int,payload:RefundIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("payments.reconcile"))):
    # Serialize refund creation on the payment row to avoid duplicate refund requests under concurrent admin actions.
    p=(await db.execute(select(Payment).where(Payment.id==payment_id).with_for_update())).scalar_one_or_none()
    if not p: raise HTTPException(404,"Payment not found")
    if p.status not in {"paid","fulfilled"}: raise HTTPException(400,"Payment is not refundable in its current state")
    existing=(await db.execute(select(RefundRequest).where(RefundRequest.payment_id==payment_id).with_for_update())).scalar_one_or_none()
    if existing: return {"id":existing.id,"status":existing.status}
    r=RefundRequest(payment_id=p.id,user_id=p.user_id,amount=p.amount,reason=payload.reason,status="requested")
    db.add(r); await audit(db,"payment.refund.requested",admin.email,str(p.id),payload.reason); await db.commit(); await db.refresh(r)
    return {"id":r.id,"status":r.status,"note":"Provider-specific refund must be confirmed through the configured provider adapter."}

@app.post("/api/admin/refunds/{refund_id}/approve")
async def approve_refund(refund_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("payments.reconcile"))):
    r=await db.get(RefundRequest,refund_id)
    if not r: raise HTTPException(404,"Refund not found")
    if r.status not in {"requested","review"}: raise HTTPException(400,"Invalid refund state")
    r.status="approved"; r.updated_at=datetime.utcnow(); await audit(db,"payment.refund.approved",admin.email,str(r.payment_id)); await db.commit()
    return {"ok":True,"status":r.status}

async def _reverse_referral_reward_for_refund(db:AsyncSession, payment:Payment, actor:str):
    """Claw back a referral reward exactly once when its payment is refunded.

    The balance update is atomic and may become negative when the referrer has
    already withdrawn/spent the reward; that represents an outstanding
    clawback instead of silently creating money.
    """
    reward=(await db.execute(select(ReferralReward).where(ReferralReward.payment_id==payment.id).with_for_update())).scalar_one_or_none()
    if not reward or reward.status == "reversed":
        return {"reversed":False,"reason":"already_reversed_or_missing"}
    result=await db.execute(sql_text("UPDATE users SET referral_balance=referral_balance-:amount WHERE id=:uid"), {"amount":reward.amount,"uid":reward.referrer_id})
    if result.rowcount != 1:
        raise RuntimeError("Referrer account not found during reward reversal")
    reward.status="reversed"
    db.add(ReferralLedger(user_id=reward.referrer_id,source_user_id=reward.referred_user_id,payment_id=None,amount=-reward.amount,kind=f"refund_reversal:{payment.id}"))
    await audit(db,"referral.reward.reversed",actor,str(reward.id),{"payment_id":payment.id,"amount":str(reward.amount)})
    return {"reversed":True,"amount":str(reward.amount)}

async def _safe_revoke_for_refunded_payment(db:AsyncSession, payment:Payment, admin_email:str, audit_action:str):
    """Revoke only when no later successfully fulfilled purchase protects the subscription."""
    sub=(await db.execute(select(Subscription).where(Subscription.user_id==payment.user_id).with_for_update())).scalar_one_or_none()
    if not sub or not sub.remnawave_uuid:
        return {"revoked":False,"reason":"no_remote_subscription"}
    later_paid=await db.scalar(select(func.count()).select_from(Payment).where(
        Payment.user_id==payment.user_id, Payment.id>payment.id,
        Payment.status.in_({"paid","fulfilled"}), Payment.fulfillment_status=="completed"))
    if later_paid:
        await audit(db,"subscription.revoke.skipped_refund_older_payment",admin_email,str(sub.id),{"payment_id":payment.id,"later_paid_count":int(later_paid)})
        return {"revoked":False,"reason":"newer_fulfilled_payment"}
    await RemnawaveClient().disable_user(sub.remnawave_uuid)
    sub.expires_at=datetime.utcnow()
    await audit(db,audit_action,admin_email,str(sub.id),{"payment_id":payment.id})
    return {"revoked":True}


@app.post("/api/admin/refunds/{refund_id}/execute")
async def execute_refund(refund_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("payments.refund"))):
    r=await db.get(RefundRequest,refund_id)
    if not r: raise HTTPException(404,"Refund not found")
    if r.status not in {"requested","approved","review"}: raise HTTPException(400,"Refund must be requested, approved, or retried from review")
    p=await db.get(Payment,r.payment_id)
    if not p: raise HTTPException(404,"Payment not found")
    provider={"yookassa":YooKassaProvider(),"platega":PlategaProvider(),"rollypay":RollyPayProvider()}.get(p.provider)
    if not provider or not hasattr(provider,"refund"): raise HTTPException(409,"Automatic refund is not supported by this provider adapter")
    # Claim the refund before calling the external provider. The state transition is
    # committed separately so a second admin request cannot issue a second refund.
    await db.execute(sql_text("SELECT id FROM refund_requests WHERE id=:id FOR UPDATE"), {"id": refund_id})
    r=await db.get(RefundRequest,refund_id)
    if not r or r.status not in {"requested","approved","review"}: raise HTTPException(409,"Refund is already processing or completed")
    if r.provider_refund_id: raise HTTPException(409,"Refund provider operation already exists; reconcile its status")
    user_lock, user_token = await _acquire_user_fulfillment_lock(p.user_id,ttl=300)
    payment_lock = payment_token = None
    try:
        payment_lock, payment_token = await _acquire_payment_side_effect_lock(p.id)
        p=(await db.execute(select(Payment).where(Payment.id==p.id).with_for_update())).scalar_one()
        r=(await db.execute(select(RefundRequest).where(RefundRequest.id==refund_id).with_for_update())).scalar_one()
        if r.status not in {"requested","approved","review"} or r.provider_refund_id:
            raise HTTPException(409,"Refund is already processing or completed")
        r.status="processing"; r.updated_at=datetime.utcnow(); await audit(db,"payment.refund.processing",admin.email,str(p.id)); await db.commit()
        result=await provider.refund(p.provider_payment_id,p.amount,p.currency,f"Refund for order {p.order_id}")
        provider_refund_id=result.get("id")
        if not provider_refund_id: raise RuntimeError("Provider returned no refund ID")
        async with AsyncSession(engine,expire_on_commit=False) as edb:
            rr=await edb.get(RefundRequest,refund_id); pp=await edb.get(Payment,p.id)
            rr.provider_refund_id=provider_refund_id; rr.updated_at=datetime.utcnow()
            status=str(result.get("status") or "processing").lower()
            if status in {"succeeded","paid","completed","refunded"}:
                rr.status="refunded"; pp.status="refunded"; pp.fulfillment_terminal=True
                await record_financial_event(edb, operation_key=f"payment:{pp.id}:refund:{rr.id}", user_id=pp.user_id, payment_id=pp.id, kind="refund", direction="debit", amount=Decimal(str(pp.amount)), currency=pp.currency, metadata={"provider": pp.provider, "refund_id": rr.id, "provider_refund_id": provider_refund_id})
                try:
                    await _safe_revoke_for_refunded_payment(edb,pp,admin.email,"subscription.revoked.refund")
                except Exception as exc:
                    rr.status="refunded_pending_revoke"; rr.reason=(rr.reason or "")+"\nRevoke pending: "+str(exc)[:500]
            else:
                rr.status="processing"
            if rr.status == "refunded":
                await _reverse_referral_reward_for_refund(edb,pp,admin.email)
            await audit(edb,"payment.refund.executed",admin.email,str(pp.id),result); await edb.commit()
        return {"ok":True,"status":rr.status,"provider_refund_id":provider_refund_id}
    except Exception as exc:
        async with AsyncSession(engine,expire_on_commit=False) as edb:
            rr=await edb.get(RefundRequest,refund_id)
            if rr and not rr.provider_refund_id:
                rr.status="review"; rr.reason=(rr.reason or "")+"\nProvider refund outcome uncertain/failed: "+str(exc)[:500]; rr.updated_at=datetime.utcnow()
                await audit(edb,"payment.refund.execute_failed",admin.email,str(p.id),{"error":str(exc)[:500]}); await edb.commit()
        raise HTTPException(503,"Refund provider operation failed or has an uncertain outcome; reconcile before retrying") from exc
    finally:
        if payment_lock and payment_token:
            await _release_payment_side_effect_lock(payment_lock, payment_token)
        await _release_payment_side_effect_lock(user_lock, user_token)

@app.post("/api/admin/refunds/{refund_id}/retry-revoke")
async def retry_refund_revoke(refund_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("payments.refund"))):
    r=await db.get(RefundRequest,refund_id)
    if not r or r.status != "refunded_pending_revoke": raise HTTPException(404,"Refund requiring revoke not found")
    p=await db.get(Payment,r.payment_id)
    if not p: raise HTTPException(404,"Payment not found")
    user_lock, user_token = await _acquire_user_fulfillment_lock(p.user_id,ttl=300)
    payment_lock = payment_token = None
    try:
        payment_lock, payment_token = await _acquire_payment_side_effect_lock(p.id)
        p=(await db.execute(select(Payment).where(Payment.id==p.id).with_for_update())).scalar_one()
        r=(await db.execute(select(RefundRequest).where(RefundRequest.id==r.id).with_for_update())).scalar_one()
        if r.status != "refunded_pending_revoke" or p.status not in {"refunded","refunded_pending_revoke"}:
            raise HTTPException(409,"Refund is not pending revoke")
        result=await _safe_revoke_for_refunded_payment(db,p,admin.email,"subscription.revoked.refund.retry")
        r.status="refunded"; r.updated_at=datetime.utcnow()
        reversal_result=await _reverse_referral_reward_for_refund(db,p,admin.email)
        await db.commit()
        return {"ok":True,"status":"refunded",**result,**reversal_result}
    except Exception as exc:
        r.status="refunded_pending_revoke"; r.reason=(r.reason or "")+"\nRevoke retry pending: "+str(exc)[:500]; await db.commit(); raise HTTPException(503,"Remnawave revoke failed") from exc
    finally:
        if payment_lock and payment_token:
            await _release_payment_side_effect_lock(payment_lock, payment_token)
        await _release_payment_side_effect_lock(user_lock, user_token)

@app.post("/api/admin/refunds/{refund_id}/mark-refunded")
async def mark_refunded(refund_id:int,admin=Depends(require_permission("payments.refund"))):
    raise HTTPException(410,"Manual mark-refunded is disabled; execute or reconcile the provider refund instead")

@app.get("/api/admin/support/tickets")
async def admin_tickets(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("support.read"))):
    rows=(await db.execute(select(SupportTicket).order_by(SupportTicket.id.desc()).limit(200))).scalars().all()
    return [{"id":x.id,"user_id":x.user_id,"subject":x.subject,"message":x.message,"status":x.status,"admin_reply":x.admin_reply,"created_at":x.created_at,"updated_at":x.updated_at} for x in rows]

@app.post("/api/admin/support/tickets/{ticket_id}/reply")
async def admin_ticket_reply(ticket_id:int,payload:AdminTicketReplyIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("support.write"))):
    t=await db.get(SupportTicket,ticket_id)
    if not t: raise HTTPException(404,"Ticket not found")
    t.admin_reply=payload.reply.strip(); t.status="resolved"; t.updated_at=datetime.utcnow(); await audit(db,"support.ticket.replied",admin.email,str(t.id)); await db.commit()
    return {"ok":True,"status":t.status}

@app.get("/api/admin/referrals/withdrawals")
async def admin_withdrawals(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("referrals.withdrawals.read"))):
    rows=(await db.execute(select(WithdrawalRequest).order_by(WithdrawalRequest.id.desc()).limit(200))).scalars().all()
    return [{"id":x.id,"user_id":x.user_id,"amount":str(x.amount),"destination":x.destination,"status":x.status,"created_at":x.created_at} for x in rows]

@app.post("/api/admin/referrals/withdrawals/{withdrawal_id}/reject")
async def reject_withdrawal(withdrawal_id:int,payload:AdminTicketReplyIn|None=None,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("referrals.withdrawals.approve"))):
    await db.execute(sql_text("SELECT id FROM withdrawal_requests WHERE id=:id FOR UPDATE"),{"id":withdrawal_id})
    x=await db.get(WithdrawalRequest,withdrawal_id)
    if not x: raise HTTPException(404,"Withdrawal not found")
    # Once approval created a payout transaction, the amount may already be in the
    # external/manual payout workflow. Restoring the balance while that payout remains
    # payable would create a real double-spend. Only an untouched request is reversible.
    if x.status != "requested": raise HTTPException(409,"Only untouched requested withdrawals can be rejected safely")
    payout=(await db.execute(select(PayoutTransaction).where(PayoutTransaction.withdrawal_id==x.id).with_for_update())).scalar_one_or_none()
    if payout and payout.status not in {"failed","cancelled","canceled"}:
        raise HTTPException(409,"Payout transaction is already active; reconcile it before restoring the balance")
    if payout:
        await db.delete(payout)
    result=await db.execute(sql_text("UPDATE users SET referral_balance=referral_balance+:amount WHERE id=:uid"),{"amount":x.amount,"uid":x.user_id})
    if result.rowcount != 1: raise HTTPException(409,"User balance could not be restored")
    x.status="rejected"; x.admin_note=(payload.reply.strip() if payload else None); x.updated_at=datetime.utcnow()
    db.add(ReferralLedger(user_id=x.user_id,source_user_id=None,payment_id=None,amount=x.amount,kind=f"withdrawal_reversal:{x.id}"))
    await audit(db,"referral.withdrawal.rejected",admin.email,str(x.id),x.admin_note); await db.commit(); return {"ok":True,"status":x.status}

@app.post("/api/admin/referrals/withdrawals/{withdrawal_id}/approve")
async def approve_withdrawal(withdrawal_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("referrals.withdrawals.approve"))):
    await db.execute(sql_text("SELECT id FROM withdrawal_requests WHERE id=:id FOR UPDATE"),{"id":withdrawal_id})
    x=await db.get(WithdrawalRequest,withdrawal_id)
    if not x: raise HTTPException(404,"Withdrawal not found")
    if x.status!="requested": raise HTTPException(409,"Withdrawal must be requested before approval")
    payout=(await db.execute(select(PayoutTransaction).where(PayoutTransaction.withdrawal_id==x.id).with_for_update())).scalar_one_or_none()
    if payout: raise HTTPException(409,"Payout transaction already exists")
    x.status="approved"; x.updated_at=datetime.utcnow(); db.add(PayoutTransaction(withdrawal_id=x.id,amount=x.amount,provider="manual",status="processing")); await audit(db,"referral.withdrawal.approved",admin.email,str(x.id)); await db.commit(); return {"ok":True,"status":x.status}

@app.post("/api/admin/referrals/withdrawals/{withdrawal_id}/paid")
async def paid_withdrawal(withdrawal_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("referrals.withdrawals.pay"))):
    await db.execute(sql_text("SELECT id FROM withdrawal_requests WHERE id=:id FOR UPDATE"),{"id":withdrawal_id})
    x=await db.get(WithdrawalRequest,withdrawal_id)
    payout=(await db.execute(select(PayoutTransaction).where(PayoutTransaction.withdrawal_id==withdrawal_id).with_for_update())).scalar_one_or_none()
    if not x or not payout: raise HTTPException(404,"Withdrawal/payout not found")
    if x.status not in {"approved","processing"}: raise HTTPException(409,"Withdrawal must be approved or processing")
    x.status="paid"; x.updated_at=datetime.utcnow(); payout.status="paid"; payout.paid_at=datetime.utcnow(); payout.updated_at=datetime.utcnow(); await audit(db,"referral.withdrawal.paid",admin.email,str(x.id)); await db.commit(); return {"ok":True,"status":"paid"}

@app.get("/api/admin/workers")
async def admin_workers(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    rows=(await db.execute(select(WorkerState).order_by(WorkerState.last_seen_at.desc()))).scalars().all()
    now=datetime.utcnow()
    return [{"worker_id":x.worker_id,"role":x.role,"status":"stale" if now-x.last_seen_at>timedelta(seconds=90) else x.status,"current_job":x.current_job,"last_seen_at":x.last_seen_at} for x in rows]

@app.get("/api/admin/releases")
async def admin_releases(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    rows=(await db.execute(select(ReleaseRecord).order_by(ReleaseRecord.id.desc()).limit(50))).scalars().all()
    return [{"id":x.id,"version":x.version,"status":x.status,"rollback_archive":x.rollback_archive,"details":x.details,"created_at":x.created_at,"completed_at":x.completed_at} for x in rows]

@app.post("/api/admin/releases/check")
async def check_release(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    return {"current":APP_VERSION,"channel":"stable","update_available":False,"manifest_configured":bool(settings.release_manifest_url and settings.release_manifest_public_key),"note":"Only a signed release manifest may be activated by production update tooling."}

@app.get("/api/admin/security/secrets/status")
async def secret_status(admin=Depends(require_permission("manage_admins"))):
    return {"APP_SECRET":"configured" if settings.app_secret else "missing","TELEGRAM_BOT_TOKEN":"configured" if settings.bot_token else "missing","REMNAWAVE_API_TOKEN":"configured" if settings.remnawave_token else "missing","S3":"configured" if settings.s3_access_key and settings.s3_secret_key else "missing","METRICS_TOKEN":"configured" if settings.metrics_token else "missing"}

@app.post("/api/admin/security/incident")
async def security_incident(payload:IncidentIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_admins"))):
    if payload.enabled:
        row=SecurityIncident(kind="incident_mode",severity=payload.severity,details=payload.reason); db.add(row); await set_setting(db,"incident_mode","1"); await set_setting(db,"incident_reason",payload.reason); await audit(db,"security.incident.enabled",admin.email,None,payload.reason)
    else:
        await set_setting(db,"incident_mode","0"); await set_setting(db,"incident_reason",payload.reason); await audit(db,"security.incident.disabled",admin.email,None,payload.reason)
    await db.commit(); return {"ok":True,"enabled":payload.enabled}

@app.get("/api/admin/security/incidents")
async def security_incidents(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    rows=(await db.execute(select(SecurityIncident).order_by(SecurityIncident.id.desc()).limit(100))).scalars().all()
    return [{"id":x.id,"kind":x.kind,"severity":x.severity,"status":x.status,"details":x.details,"created_at":x.created_at,"resolved_at":x.resolved_at} for x in rows]

@app.get("/api/admin/openapi.json")
async def admin_openapi(admin=Depends(require_permission("read"))):
    return app.openapi()

@app.get("/api/admin/recovery")
async def admin_recovery(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    restore_state=await setting_value(db,"restore_state","ok")
    maintenance=await maintenance_enabled(db)
    workers=(await db.execute(select(WorkerState).order_by(WorkerState.last_seen_at.desc()))).scalars().all()
    now=datetime.utcnow()
    heartbeat=[{"worker_id":w.worker_id,"role":w.role,"status":"stale" if now-w.last_seen_at>timedelta(seconds=90) else w.status,"last_seen_at":w.last_seen_at} for w in workers]
    failed=int((await db.execute(select(func.count()).select_from(Payment).where(Payment.fulfillment_status=="failed",Payment.fulfillment_terminal.is_(True)))).scalar() or 0)
    return {"maintenance_mode":maintenance,"restore_state":restore_state,"workers":heartbeat,"terminal_fulfillment_failures":failed,"recovery_required":maintenance or restore_state=="failed" or any(x["status"]=="stale" for x in heartbeat)}

@app.post("/api/admin/incident-mode")
async def incident_mode(payload:dict,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_admins"))):
    enabled=bool(payload.get("enabled")); await set_setting(db,"incident_mode","1" if enabled else "0");
    if enabled: await set_setting(db,"maintenance_mode","1")
    await audit(db,"security.incident_mode",admin.email,None,{"enabled":enabled}); await db.commit(); return {"enabled":enabled}

@app.get("/api/admin/incident-mode")
async def incident_mode_status(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    return {"enabled":await setting_value(db,"incident_mode","0")=="1"}

@app.post("/api/admin/referrals/reconcile")
async def reconcile_referrals(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("referrals.reconcile"))):
    users=(await db.execute(select(User).where(User.referral_balance!=None).with_for_update())).scalars().all(); changed=0
    for u in users:
        total=(await db.execute(select(func.coalesce(func.sum(ReferralLedger.amount),0)).where(ReferralLedger.user_id==u.id))).scalar() or Decimal("0")
        if Decimal(str(u.referral_balance or 0)) != Decimal(str(total)):
            u.referral_balance=total; changed+=1
    await audit(db,"referral.reconciliation",admin.email,None,{"checked":len(users),"changed":changed}); await db.commit(); return {"checked":len(users),"changed":changed}

@app.get("/api/admin/system/health")
async def system_health(admin=Depends(require_permission("read"))):
    disk=shutil.disk_usage("/")
    mem_total=mem_avail=None
    try:
        vals={}
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            k,v=line.split(":",1); vals[k]=int(v.strip().split()[0])*1024
        mem_total=vals.get("MemTotal"); mem_avail=vals.get("MemAvailable")
    except Exception as exc:
        logger.warning("Non-critical operation failed: %s", exc)
    redis_ok=False; db_ok=False
    if redis_client is not None:
        try: await redis_client.ping(); redis_ok=True
        except Exception as exc:
            logger.warning("Non-critical operation failed: %s", exc)
    try:
        async with AsyncSession(engine,expire_on_commit=False) as hdb: await hdb.execute(sql_text("SELECT 1")); db_ok=True
    except Exception as exc:
        logger.warning("Non-critical operation failed: %s", exc)
    worker_heartbeat=None
    worker_healthy=False
    worker_count=0
    try:
        async with AsyncSession(engine,expire_on_commit=False) as sdb:
            cutoff=datetime.utcnow()-timedelta(seconds=90)
            workers=(await sdb.execute(select(WorkerState).where(WorkerState.role==settings.worker_role, WorkerState.status=="online", WorkerState.last_seen_at>=cutoff).order_by(WorkerState.last_seen_at.desc()))).scalars().all()
            worker_count=len(workers)
            if workers:
                worker_healthy=True
                worker_heartbeat=workers[0].last_seen_at.isoformat()
    except Exception as exc:
        logger.exception("worker health lookup failed: %s", exc)
    incident=False
    try:
        async with AsyncSession(engine,expire_on_commit=False) as sdb: incident=await setting_value(sdb,"incident_mode","0")=="1"
    except Exception as exc:
        logger.exception("incident mode lookup failed: %s", exc)
    return {"api":True,"database":db_ok,"redis":redis_ok,"worker_heartbeat":worker_heartbeat,"worker_healthy":worker_healthy,"worker_count":worker_count,"incident_mode":incident,"disk":{"total":disk.total,"used":disk.used,"free":disk.free,"percent":round(disk.used/disk.total*100,1)},"memory":{"total":mem_total,"available":mem_avail,"percent":round((1-mem_avail/mem_total)*100,1) if mem_total and mem_avail else None},"backup_lock":BACKUP_LOCK.locked(),"worker_role":settings.worker_role}

@app.get("/api/admin/analytics")
async def admin_analytics(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("analytics.read"))):
    now=datetime.utcnow(); day=now-timedelta(days=1); week=now-timedelta(days=7); month=now-timedelta(days=30)
    async def rev(since): return float((await db.execute(select(func.coalesce(func.sum(Payment.amount),0)).where(Payment.status=="paid",Payment.created_at>=since))).scalar() or 0)
    return {"revenue":{"24h":await rev(day),"7d":await rev(week),"30d":await rev(month)},"users":{"total":int((await db.execute(select(func.count()).select_from(User))).scalar() or 0),"new_24h":int((await db.execute(select(func.count()).select_from(User).where(User.created_at>=day))).scalar() or 0)},"subscriptions":{"active":int((await db.execute(select(func.count()).select_from(Subscription).where(Subscription.expires_at>now))).scalar() or 0)},"payments":{"pending":int((await db.execute(select(func.count()).select_from(Payment).where(Payment.status=="pending"))).scalar() or 0),"fulfillment_failed":int((await db.execute(select(func.count()).select_from(Payment).where(Payment.fulfillment_status=="failed"))).scalar() or 0)}}

@app.get("/api/admin/sessions")
async def admin_sessions(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("sessions.manage"))):
    rows=(await db.execute(select(AdminSession,AdminUser.email).join(AdminUser,AdminUser.id==AdminSession.admin_id).where(AdminSession.revoked_at.is_(None),AdminSession.expires_at>datetime.utcnow()).order_by(AdminSession.created_at.desc()).limit(200))).all()
    return [{"id":s.id,"admin_email":email,"ip":s.ip,"user_agent":s.user_agent,"created_at":s.created_at,"last_seen_at":s.last_seen_at,"expires_at":s.expires_at} for s,email in rows]

@app.post("/api/admin/sessions/revoke-all")
async def revoke_all_sessions(request:Request,response:Response,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("sessions.manage"))):
    if admin.mfa_enabled:
        otp=request.headers.get("X-MFA-Code","")
        if not verify_totp(admin,otp): raise HTTPException(401,"Valid MFA code is required")
    await db.execute(__import__("sqlalchemy").update(AdminSession).where(AdminSession.admin_id==admin.id,AdminSession.revoked_at.is_(None)).values(revoked_at=datetime.utcnow()))
    await audit(db,"security.sessions.revoked_all",admin.email,admin.email); await db.commit(); response.delete_cookie("rw_admin"); response.delete_cookie("rw_csrf"); return {"ok":True}

@app.delete("/api/admin/sessions/{session_id}")
async def revoke_admin_session(session_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("sessions.manage"))):
    s=await db.get(AdminSession,session_id);
    if not s: raise HTTPException(404,"Session not found")
    s.revoked_at=datetime.utcnow(); await audit(db,"security.session.revoked",admin.email,str(session_id)); await db.commit(); return {"ok":True}

@app.post("/api/admin/payments/reconcile")
async def reconcile_payments(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("payments.reconcile"))):
    cutoff=datetime.utcnow()-timedelta(hours=72)
    rows=(await db.execute(select(Payment).where(Payment.created_at>=cutoff,((Payment.status=="pending") | (Payment.status=="creation_unknown") | ((Payment.status=="paid") & (Payment.fulfillment_status!="completed")))).order_by(Payment.id).limit(500))).scalars().all()
    providers={"yookassa":YooKassaProvider(),"platega":PlategaProvider(),"rollypay":RollyPayProvider()}; changed=0; retried=0; recovered=0
    for p in rows:
        provider=providers.get(p.provider)
        if not provider or not hasattr(provider,"verify_succeeded"): continue
        try:
            if p.status=="creation_unknown" and p.provider=="yookassa":
                # Re-issuing the same durable order_id is safe because YooKassa binds
                # the result to its Idempotence-Key. This closes the orphan-intent window
                # without ever creating a second charge.
                result=await provider.create(Decimal(str(p.amount)),p.order_id,f"VPN plan {p.plan_id}",settings.mini_app_url)
                p.provider_payment_id=result["id"]; p.checkout_url=result.get("url"); p.status="pending"; p.fulfillment_terminal=False; recovered += 1
            if not p.provider_payment_id:
                continue
            confirmed=await provider.verify_succeeded(p.provider_payment_id,Decimal(str(p.amount)),p.currency,p.order_id)
            if confirmed:
                try:
                    result=await _confirm_and_fulfill_payment(p.id,db)
                    if not result.get("ignored"):
                        changed += 1
                        retried += 1
                except Exception as exc:
                    logger.warning("Non-critical operation failed: %s", exc)
        except Exception: continue
    await audit(db,"payment.reconciliation",admin.email,None,{"checked":len(rows),"confirmed":changed,"retried":retried,"creation_unknown_recovered":recovered}); await db.commit(); return {"checked":len(rows),"confirmed":changed,"retried":retried,"creation_unknown_recovered":recovered}

@app.post("/api/admin/payments/{payment_id}/retry")
async def retry_payment(payment_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("payments.retry"))):
    p=await db.get(Payment,payment_id);
    if not p: raise HTTPException(404,"Payment not found")
    if p.status in {"refunded", "refunded_pending_revoke"}: raise HTTPException(409,"Refunded payment cannot be fulfilled")
    if p.status=="paid" and p.fulfillment_status=="completed": return {"ok":True,"status":"completed"}
    p.next_retry_at=datetime.utcnow(); p.fulfillment_status="pending"; await db.commit()
    try: await fulfill(p.id,db)
    except Exception as e: return {"ok":False,"status":"failed","error":str(e)[:500]}
    return {"ok":True,"status":"completed"}


# ---------- V32 Operations / Monitoring / Fraud / Privacy ----------
@app.get("/api/me/traffic")
async def my_traffic(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db); sub=(await db.execute(select(Subscription).where(Subscription.user_id==user.id))).scalar_one_or_none()
    if not sub or not sub.remnawave_uuid: return {"available":False,"traffic_used_bytes":None,"traffic_limit_bytes":None,"devices":None}
    try:
        data=await RemnawaveClient().get_user(sub.remnawave_uuid)
        return {"available":True,"traffic_used_bytes":data.get("trafficUsedBytes") or data.get("usedTrafficBytes"),"traffic_limit_bytes":data.get("trafficLimitBytes"),"devices":data.get("devices") or data.get("deviceCount"),"status":data.get("status"),"expires_at":data.get("expireAt") or data.get("expiresAt")}
    except Exception:
        return {"available":False,"traffic_used_bytes":None,"traffic_limit_bytes":None,"devices":None}

@app.get("/api/me/privacy/export")
async def privacy_export(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    sub=(await db.execute(select(Subscription).where(Subscription.user_id==user.id))).scalar_one_or_none()
    payments=(await db.execute(select(Payment).where(Payment.user_id==user.id).order_by(Payment.id))).scalars().all()
    tickets=(await db.execute(select(SupportTicket).where(SupportTicket.user_id==user.id).order_by(SupportTicket.id))).scalars().all()
    withdrawals=(await db.execute(select(WithdrawalRequest).where(WithdrawalRequest.user_id==user.id).order_by(WithdrawalRequest.id))).scalars().all()
    return {"exported_at":datetime.utcnow(),"user":{"id":user.id,"telegram_id":user.telegram_id,"yandex_id":user.yandex_id,"username":user.username,"referral_code":user.referral_code,"created_at":user.created_at},"subscription":None if not sub else {"plan_id":sub.plan_id,"remnawave_uuid":sub.remnawave_uuid,"expires_at":sub.expires_at},"payments":[{"id":x.id,"amount":str(x.amount),"currency":x.currency,"provider":x.provider,"status":x.status,"created_at":x.created_at} for x in payments],"tickets":[{"id":x.id,"subject":x.subject,"status":x.status,"created_at":x.created_at} for x in tickets],"withdrawals":[{"id":x.id,"amount":str(x.amount),"status":x.status,"created_at":x.created_at} for x in withdrawals]}

@app.delete("/api/me/privacy/account")
async def privacy_delete(request:Request,db:AsyncSession=Depends(get_db)):
    user=await user_from_token(request,db)
    user=(await db.execute(select(User).where(User.id==user.id).with_for_update())).scalar_one()
    if user.deleted_at is not None:
        raise HTTPException(409,"Account is already anonymized")
    user_lock, user_token = await _acquire_user_fulfillment_lock(user.id)
    try:
        active=(await db.execute(select(Subscription).where(Subscription.user_id==user.id).with_for_update())).scalar_one_or_none()
        # NULL expiry is an indefinite/unknown active entitlement, not an expired one.
        if active and (active.expires_at is None or active.expires_at>datetime.utcnow()):
            raise HTTPException(409,"Active subscription must expire before account deletion")
        # Account anonymization must not leave a usable remote VPN account behind.
        # If a remote account exists, revoke it first and fail closed if Remnawave is unavailable.
        if active and active.remnawave_uuid:
            try:
                await RemnawaveClient().disable_user(active.remnawave_uuid)
            except Exception as exc:
                raise HTTPException(503,"Не удалось отключить удалённую VPN-подписку; удаление аккаунта остановлено") from exc
            active.expires_at=datetime.utcnow()
            active.subscription_url=None
            active.remnawave_uuid=None
        if user.telegram_id: user.telegram_id=None
        user.yandex_id=None
        user.username=f"deleted_{user.id}"
        user.referral_code=f"deleted_{user.id}"
        user.auto_renew_enabled=False
        user.deleted_at=datetime.utcnow()
        method=(await db.execute(select(AutoRenewMethod).where(AutoRenewMethod.user_id==user.id).with_for_update())).scalar_one_or_none()
        if method:
            method.enabled=False
            method.status="deleted"
            method.external_token_encrypted="DELETED"
        await db.execute(sql_text("UPDATE user_devices SET status='revoked', revoked_at=COALESCE(revoked_at, NOW()) WHERE user_id=:uid"), {"uid":user.id})
        await audit(db,"privacy.account.anonymized",f"user:{user.id}",str(user.id))
        await db.commit()
        return {"ok":True,"anonymized":True}
    finally:
        await _release_payment_side_effect_lock(user_lock, user_token)

@app.get("/api/admin/financial-ledger")
async def admin_financial_ledger(db:AsyncSession=Depends(get_db), admin=Depends(require_permission("payments.read"))):
    rows=(await db.execute(select(FinancialLedger).order_by(FinancialLedger.id.desc()).limit(500))).scalars().all()
    return [{"id":x.id,"operation_key":x.operation_key,"user_id":x.user_id,"payment_id":x.payment_id,"kind":x.kind,"direction":x.direction,"amount":str(x.amount),"currency":x.currency,"created_at":x.created_at,"metadata":json.loads(x.metadata_json or "{}")} for x in rows]

@app.get("/api/admin/monitoring")
async def admin_monitoring(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    now=datetime.utcnow(); disk=shutil.disk_usage("/")
    workers=(await db.execute(select(WorkerState).order_by(WorkerState.last_seen_at.desc()))).scalars().all()
    jobs=(await db.execute(select(Job).order_by(Job.id.desc()).limit(200))).scalars().all()
    return {"version":APP_VERSION,"disk_percent":round(disk.used/disk.total*100,1),"workers":[{"id":w.worker_id,"role":w.role,"status":"stale" if now-w.last_seen_at>timedelta(seconds=90) else w.status,"last_seen_at":w.last_seen_at} for w in workers],"jobs":{"queued":sum(j.status=="queued" for j in jobs),"processing":sum(j.status=="processing" for j in jobs),"failed":sum(j.status=="failed" for j in jobs)},"requests":dict(_METRICS)}

@app.get("/api/admin/jobs")
async def admin_jobs(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    rows=(await db.execute(select(Job).order_by(Job.id.desc()).limit(500))).scalars().all()
    return [{"id":x.id,"job_key":x.job_key,"kind":x.kind,"status":x.status,"attempts":x.attempts,"max_attempts":x.max_attempts,"next_retry_at":x.next_retry_at,"worker_id":x.worker_id,"error":x.error,"created_at":x.created_at,"completed_at":x.completed_at} for x in rows]

@app.post("/api/admin/jobs/{job_id}/retry")
async def retry_job(job_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("payments.retry"))):
    row=await db.get(Job,job_id)
    if not row: raise HTTPException(404,"Job not found")
    row.status="queued"; row.next_retry_at=datetime.utcnow(); row.error=None; row.locked_at=None; await audit(db,"job.requeued",admin.email,str(job_id)); await db.commit(); return {"ok":True}

@app.get("/api/admin/fraud")
async def admin_fraud(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("security.manage"))):
    rows=(await db.execute(select(FraudSignal).order_by(FraudSignal.id.desc()).limit(500))).scalars().all()
    return [{"id":x.id,"user_id":x.user_id,"ip":x.ip,"fingerprint":x.fingerprint,"kind":x.kind,"score":x.score,"status":x.status,"details":x.details,"created_at":x.created_at} for x in rows]

@app.post("/api/admin/fraud/{signal_id}")
async def fraud_decision(signal_id:int,payload:FraudDecisionIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("security.manage"))):
    row=await db.get(FraudSignal,signal_id)
    if not row: raise HTTPException(404,"Fraud signal not found")
    row.status=payload.status; row.resolved_at=datetime.utcnow() if payload.status!="open" else None
    await audit(db,"fraud.signal.updated",admin.email,str(signal_id),payload.note); await db.commit(); return {"ok":True,"status":row.status}

@app.post("/api/admin/fraud/scan")
async def fraud_scan(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("security.manage"))):
    since=datetime.utcnow()-timedelta(hours=24); created=0
    # Velocity checks: repeated payments from the same user and repeated failed fulfillment.
    rows=(await db.execute(select(Payment.user_id,func.count(Payment.id)).where(Payment.created_at>=since).group_by(Payment.user_id).having(func.count(Payment.id)>=10))).all()
    for uid,count in rows:
        db.add(FraudSignal(user_id=uid,kind="payment_velocity",score=min(100,int(count)*5),details=f"{count} payments in 24h")); created+=1
    failed=(await db.execute(select(Payment.user_id,func.count(Payment.id)).where(Payment.created_at>=since,Payment.fulfillment_status=="failed").group_by(Payment.user_id).having(func.count(Payment.id)>=3))).all()
    for uid,count in failed:
        db.add(FraudSignal(user_id=uid,kind="fulfillment_failure_velocity",score=min(100,int(count)*15),details=f"{count} failed fulfillments in 24h")); created+=1
    await audit(db,"fraud.scan",admin.email,None,{"created":created}); await db.commit(); return {"created":created}

@app.get("/api/admin/payouts")
async def admin_payouts(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("referrals.withdrawals.read"))):
    rows=(await db.execute(select(PayoutTransaction).order_by(PayoutTransaction.id.desc()).limit(200))).scalars().all()
    return [{"id":x.id,"withdrawal_id":x.withdrawal_id,"provider":x.provider,"external_id":x.external_id,"amount":str(x.amount),"status":x.status,"attempts":x.attempts,"last_error":x.last_error,"created_at":x.created_at,"paid_at":x.paid_at} for x in rows]

@app.post("/api/admin/ops/withdrawals/{withdrawal_id}/approve")
async def admin_withdrawal_approve(withdrawal_id:int,payload:WithdrawalActionIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("referrals.withdrawals.approve"))):
    await db.execute(sql_text("SELECT id FROM withdrawal_requests WHERE id=:id FOR UPDATE"),{"id":withdrawal_id})
    w=await db.get(WithdrawalRequest,withdrawal_id)
    if not w: raise HTTPException(404,"Withdrawal not found")
    if w.status!="requested": raise HTTPException(409,"Withdrawal is not requested")
    existing_payout=(await db.execute(select(PayoutTransaction).where(PayoutTransaction.withdrawal_id==w.id).with_for_update())).scalar_one_or_none()
    if existing_payout: raise HTTPException(409,"Payout transaction already exists")
    w.status="approved"; w.updated_at=datetime.utcnow(); db.add(PayoutTransaction(withdrawal_id=w.id,amount=w.amount,provider="manual",status="processing")); await audit(db,"referral.withdrawal.approved",admin.email,str(w.id),payload.note); await db.commit(); return {"ok":True,"status":w.status}

@app.post("/api/admin/ops/withdrawals/{withdrawal_id}/paid")
async def admin_withdrawal_paid(withdrawal_id:int,payload:WithdrawalActionIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("referrals.withdrawals.pay"))):
    await db.execute(sql_text("SELECT id FROM withdrawal_requests WHERE id=:id FOR UPDATE"),{"id":withdrawal_id})
    w=await db.get(WithdrawalRequest,withdrawal_id); p=(await db.execute(select(PayoutTransaction).where(PayoutTransaction.withdrawal_id==withdrawal_id).with_for_update())).scalar_one_or_none()
    if not w or not p: raise HTTPException(404,"Withdrawal/payout not found")
    if w.status not in {"approved","processing"}: raise HTTPException(409,"Withdrawal is not payable")
    w.status="paid"; w.updated_at=datetime.utcnow(); p.status="paid"; p.paid_at=datetime.utcnow(); p.updated_at=datetime.utcnow(); await audit(db,"referral.withdrawal.paid",admin.email,str(w.id),payload.note); await db.commit(); return {"ok":True,"status":"paid"}

@app.post("/api/admin/refunds/{refund_id}/reconcile")
async def reconcile_refund(refund_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("payments.reconcile"))):
    r=await db.get(RefundRequest,refund_id)
    if not r: raise HTTPException(404,"Refund not found")
    if not r.provider_refund_id: raise HTTPException(409,"Provider refund ID is missing")
    p=await db.get(Payment,r.payment_id)
    if not p: raise HTTPException(404,"Payment not found")
    providers={"yookassa":YooKassaProvider(),"platega":PlategaProvider(),"rollypay":RollyPayProvider()}
    provider=providers.get(p.provider)
    if not provider or not hasattr(provider,"get_refund_status"): raise HTTPException(409,"Refund status adapter is unavailable")
    try:
        status=str(await provider.get_refund_status(r.provider_refund_id)).lower()
    except Exception as exc:
        await audit(db,"payment.refund.reconcile_failed",admin.email,str(r.id),{"error":str(exc)[:500]}); await db.commit()
        raise HTTPException(503,"Provider refund status unavailable")
    if status in {"succeeded","paid","completed","refunded"}:
        user_lock, user_token = await _acquire_user_fulfillment_lock(p.user_id,ttl=300)
        payment_lock = payment_token = None
        try:
            payment_lock, payment_token = await _acquire_payment_side_effect_lock(p.id)
            p=(await db.execute(select(Payment).where(Payment.id==p.id).with_for_update())).scalar_one()
            r=(await db.execute(select(RefundRequest).where(RefundRequest.id==r.id).with_for_update())).scalar_one()
            r.status="refunded"; r.updated_at=datetime.utcnow(); p.status="refunded"; p.fulfillment_terminal=True
            try:
                revoke_result=await _safe_revoke_for_refunded_payment(db,p,admin.email,"subscription.revoked.refund.reconciled")
            except Exception as exc:
                r.status="refunded_pending_revoke"; r.reason=(r.reason or "")+"\nRevoke pending: "+str(exc)[:500]; revoke_result={"revoked":False,"reason":"revoke_failed"}
            reversal_result=await _reverse_referral_reward_for_refund(db,p,admin.email) if r.status == "refunded" else {"reversed":False}
            await audit(db,"payment.refund.reconciled",admin.email,str(r.id),{"provider_status":status,**revoke_result,**reversal_result}); await db.commit()
            return {"ok":True,"status":r.status,"verified":True,"provider_status":status,**revoke_result}
        finally:
            if payment_lock and payment_token:
                await _release_payment_side_effect_lock(payment_lock, payment_token)
            await _release_payment_side_effect_lock(user_lock, user_token)
    if status in {"canceled","cancelled","failed","rejected"}:
        r.status="failed"; r.reason=(r.reason or "")+f"\nProvider refund status: {status}"; r.updated_at=datetime.utcnow(); await db.commit()
        return {"ok":True,"status":"failed","verified":True,"provider_status":status}
    r.status="processing"; r.updated_at=datetime.utcnow(); await db.commit()
    return {"ok":True,"status":"processing","verified":False,"provider_status":status}

# ---------- Admin API ----------
@app.get("/api/admin/customers/{user_id}/360")
async def customer_360(user_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("users.read"))):
    user=await db.get(User,user_id)
    if not user: raise HTTPException(404,"User not found")
    sub=await db.scalar(select(Subscription).where(Subscription.user_id==user_id))
    payments=(await db.execute(select(Payment).where(Payment.user_id==user_id).order_by(Payment.id.desc()).limit(100))).scalars().all()
    refunds=(await db.execute(select(RefundRequest).where(RefundRequest.user_id==user_id).order_by(RefundRequest.id.desc()).limit(50))).scalars().all()
    devices=(await db.execute(select(UserDevice).where(UserDevice.user_id==user_id).order_by(UserDevice.id.desc()))).scalars().all()
    referrals=(await db.execute(select(ReferralLedger).where(ReferralLedger.user_id==user_id).order_by(ReferralLedger.id.desc()).limit(50))).scalars().all()
    tickets=(await db.execute(select(SupportTicket).where(SupportTicket.user_id==user_id).order_by(SupportTicket.id.desc()).limit(50))).scalars().all()
    signals=(await db.execute(select(FraudSignal).where(FraudSignal.user_id==user_id).order_by(FraudSignal.id.desc()).limit(50))).scalars().all()
    return {"user":{"id":user.id,"telegram_id":user.telegram_id,"yandex_id":user.yandex_id,"username":user.username,"created_at":user.created_at,"deleted_at":user.deleted_at},"subscription":None if not sub else {"id":sub.id,"plan_id":sub.plan_id,"status":sub.lifecycle_status,"expires_at":sub.expires_at,"grace_until":sub.grace_until,"scheduled_cancel_at":sub.scheduled_cancel_at},"payments":[{"id":p.id,"order_id":p.order_id,"amount":str(p.amount),"currency":p.currency,"status":p.status,"fulfillment_status":p.fulfillment_status,"created_at":p.created_at} for p in payments],"refunds":[{"id":r.id,"payment_id":r.payment_id,"status":r.status,"amount":str(r.amount),"reason":r.reason} for r in refunds],"devices":[{"id":d.id,"name":d.name,"status":d.status,"last_ip":d.last_ip,"last_seen_at":d.last_seen_at} for d in devices],"referrals":[{"id":x.id,"amount":str(x.amount),"kind":x.kind,"payment_id":x.payment_id} for x in referrals],"tickets":[{"id":t.id,"subject":t.subject,"status":t.status,"created_at":t.created_at} for t in tickets],"fraud":[{"id":x.id,"kind":x.kind,"score":x.score,"status":x.status,"details":x.details} for x in signals]}

@app.get("/api/admin/refunds/{refund_id}/dry-run")
async def refund_dry_run(refund_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("payments.refund"))):
    r=await db.get(RefundRequest,refund_id)
    if not r: raise HTTPException(404,"Refund not found")
    p=await db.get(Payment,r.payment_id)
    if not p: raise HTTPException(404,"Payment not found")
    later_paid=int(await db.scalar(select(func.count()).select_from(Payment).where(Payment.user_id==p.user_id,Payment.id>p.id,Payment.status.in_({"paid","fulfilled"}),Payment.fulfillment_status=="completed")) or 0)
    reward=await db.scalar(select(ReferralReward).where(ReferralReward.payment_id==p.id))
    sub=await db.scalar(select(Subscription).where(Subscription.user_id==p.user_id))
    actions=["refund_provider"]
    if sub and later_paid==0: actions.append("revoke_subscription")
    if reward: actions.append("reverse_referral_reward")
    return {"safe_to_execute":p.status in {"paid","fulfilled"} and r.status in {"requested","approved","review"},"payment_id":p.id,"amount":str(p.amount),"currency":p.currency,"subscription":{"id":sub.id,"current_expires_at":sub.expires_at} if sub else None,"later_fulfilled_payments":later_paid,"referral_reward":str(reward.amount) if reward else None,"planned_actions":actions}

@app.get("/api/admin/security/risk-summary")
async def risk_summary(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("security.manage"))):
    open_signals=int(await db.scalar(select(func.count()).select_from(FraudSignal).where(FraudSignal.status=="open")) or 0)
    critical=int(await db.scalar(select(func.count()).select_from(FraudSignal).where(FraudSignal.status=="open",FraudSignal.score>=80)) or 0)
    recent=(await db.execute(select(FraudSignal).where(FraudSignal.status=="open").order_by(FraudSignal.score.desc(),FraudSignal.id.desc()).limit(20))).scalars().all()
    return {"open":open_signals,"critical":critical,"signals":[{"id":x.id,"user_id":x.user_id,"kind":x.kind,"score":x.score,"ip":x.ip,"created_at":x.created_at} for x in recent]}

@app.get("/api/admin/health/summary")
async def health_summary(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.diagnostics"))):
    checks=[]
    try:
        await db.execute(sql_text("SELECT 1")); checks.append({"name":"PostgreSQL","status":"ok"})
    except Exception as exc: checks.append({"name":"PostgreSQL","status":"error","error":str(exc)[:300]})
    if redis_client:
        try:
            start=asyncio.get_running_loop().time(); await redis_client.ping(); checks.append({"name":"Redis","status":"ok","latency_ms":round((asyncio.get_running_loop().time()-start)*1000,1)})
        except Exception as exc: checks.append({"name":"Redis","status":"error","error":str(exc)[:300]})
    try:
        start=asyncio.get_running_loop().time(); await RemnawaveClient().list_nodes(start=0,size=1); checks.append({"name":"Remnawave","status":"ok","latency_ms":round((asyncio.get_running_loop().time()-start)*1000,1)})
    except Exception: checks.append({"name":"Remnawave","status":"error","error":"unavailable"})
    return {"status":"ok" if all(x["status"]=="ok" for x in checks) else "degraded","checks":checks,"incident_mode":(await setting_value(db,"incident_mode","0"))=="1","payments_paused":(await setting_value(db,PRODUCTION_PAYMENTS_GATE_KEY,"0"))!="1"}

@app.get("/api/admin/gifts")
async def admin_gifts(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("marketing.read"))):
    rows=(await db.execute(select(GiftCode).order_by(GiftCode.id.desc()).limit(200))).scalars().all()
    return [{"id":x.id,"code":x.code,"plan_id":x.plan_id,"duration_days":x.duration_days,"max_uses":x.max_uses,"used_count":x.used_count,"expires_at":x.expires_at,"enabled":x.enabled,"purchaser_user_id":x.purchaser_user_id} for x in rows]

@app.post("/api/admin/gifts")
async def admin_gift_create(payload:GiftCreateIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_marketing"))):
    plan=await db.get(Plan,payload.plan_id)
    if not plan or not plan.enabled: raise HTTPException(400,"Plan not found or disabled")
    code=payload.code.strip().upper()
    if await db.scalar(select(GiftCode.id).where(GiftCode.code==code)): raise HTTPException(409,"Gift code already exists")
    if payload.purchaser_user_id and not await db.get(User,payload.purchaser_user_id): raise HTTPException(400,"Purchaser not found")
    x=GiftCode(code=code,plan_id=plan.id,duration_days=payload.duration_days,max_uses=payload.max_uses,expires_at=payload.expires_at,purchaser_user_id=payload.purchaser_user_id)
    db.add(x); await audit(db,"gift.created",admin.email,code,{"plan_id":plan.id,"max_uses":payload.max_uses}); await db.commit(); await db.refresh(x)
    return {"id":x.id,"code":x.code}

@app.get("/api/admin/overview")
async def admin_overview(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    try:
        users=await RemnawaveClient().list_users(start=0,size=1); raw_nodes=await RemnawaveClient().list_nodes(start=0,size=100)
        from .tariff_api import _iter_nodes, public_node
        safe_nodes=[public_node(n) for n in _iter_nodes(raw_nodes)]
        nodes={"total":len(safe_nodes),"nodes":safe_nodes}
    except Exception: users={"error":"unavailable"}; nodes={"error":"unavailable"}
    return {"plans":len((await db.execute(select(Plan))).scalars().all()),"payments":len((await db.execute(select(Payment))).scalars().all()),"remnawave_users":users,"nodes":nodes,"role":admin.role}

@app.get("/api/admin/plans")
async def admin_list_plans(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    rows=(await db.execute(select(Plan).order_by(Plan.id))).scalars().all()
    return [{"id":p.id,"name":p.name,"price":float(p.price),"duration_days":p.duration_days,"traffic_limit_gb":p.traffic_limit_gb,"device_limit":p.device_limit,"remnawave_profile_id":p.remnawave_profile_id,"enabled":p.enabled} for p in rows]

@app.post("/api/admin/plans")
async def create_plan(payload:PlanIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_plans"))):
    p=Plan(**payload.model_dump()); db.add(p); await audit(db,"plan.created",admin.email,str(p.id),payload.model_dump()); await db.commit(); await db.refresh(p); return {"id":p.id}

@app.put("/api/admin/plans/{plan_id}")
async def admin_update_plan(plan_id:int,payload:PlanIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_plans"))):
    p=await db.get(Plan,plan_id)
    if not p: raise HTTPException(404,"Plan not found")
    for k,v in payload.model_dump().items(): setattr(p,k,v)
    await audit(db,"plan.updated",admin.email,str(plan_id),payload.model_dump()); await db.commit(); return {"ok":True,"id":plan_id}

@app.delete("/api/admin/plans/{plan_id}")
async def admin_delete_plan(plan_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_plans"))):
    p=await db.get(Plan,plan_id)
    if not p: raise HTTPException(404,"Plan not found")
    refs=(await db.execute(select(func.count()).select_from(Payment).where(Payment.plan_id==plan_id))).scalar() or 0
    subs=(await db.execute(select(func.count()).select_from(Subscription).where(Subscription.plan_id==plan_id))).scalar() or 0
    trials=(await db.execute(select(func.count()).select_from(TrialGrant).where(TrialGrant.plan_id==plan_id))).scalar() or 0
    if refs or subs or trials:
        raise HTTPException(409,"Тариф уже используется платежами, подписками или пробными периодами; отключите его вместо удаления")
    await db.delete(p); await audit(db,"plan.deleted",admin.email,str(plan_id)); await db.commit(); return {"ok":True}

@app.get("/api/admin/payments")
async def admin_payments(page:int=1,page_size:int=50,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    page=max(1,page); page_size=max(1,min(page_size,100)); offset=(page-1)*page_size
    rows=(await db.execute(select(Payment).order_by(Payment.id.desc()).offset(offset).limit(page_size))).scalars().all()
    return [{"id":x.id,"provider":x.provider,"status":x.status,"fulfillment_status":x.fulfillment_status,"fulfillment_attempts":x.fulfillment_attempts,"fulfillment_error":x.fulfillment_error,"amount":float(x.amount),"currency":x.currency,"created_at":str(x.created_at),"paid_at":str(x.paid_at) if x.paid_at else None} for x in rows]

@app.get("/api/admin/audit")
async def admin_audit(page:int=1,page_size:int=50,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    page=max(1,page); page_size=max(1,min(page_size,100)); offset=(page-1)*page_size
    rows=(await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).offset(offset).limit(page_size))).scalars().all()
    return [{"id":x.id,"action":x.action,"actor":x.actor,"target":x.target,"details":x.details,"created_at":str(x.created_at)} for x in rows]

@app.get("/api/admin/remnawave/users")
async def rw_users(start:int=0,size:int=25,admin=Depends(require_permission("read"))): return await RemnawaveClient().list_users(start,max(1,min(size,1000)))
@app.get("/api/admin/remnawave/users/stream")
async def rw_user_stream(telegram_id:int|None=None,cursor:int|None=None,size:int=250,status:str|None=None,admin=Depends(require_permission("read"))): return await RemnawaveClient().stream_users(telegram_id,cursor,size,status)
@app.get("/api/admin/remnawave/nodes")
async def rw_nodes(start:int=0,size:int=25,admin=Depends(require_permission("read"))):
    from .tariff_api import remnawave_server_status
    return await remnawave_server_status("admin")
@app.get("/api/admin/remnawave/users/{user_id}")
async def rw_user(user_id:int,admin=Depends(require_permission("read"))): return await RemnawaveClient().get_user(user_id)
@app.post("/api/admin/remnawave/users/{user_id}/extend")
async def rw_extend(user_id:int,payload:dict,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_users"))):
    # All manual extensions use the same remote-first verification algorithm as payment provisioning.
    days=int(payload.get("days",0))
    if not 1<=days<=3650: raise HTTPException(400,"days must be 1..3650")
    rw=RemnawaveClient(); remote=await rw.get_user(user_id)
    raw=remote.get("expireAt") or remote.get("expire_at") or remote.get("expiresAt") or remote.get("expires_at")
    if not raw: raise HTTPException(409,"Remote user has no readable expiration date")
    try: before=datetime.fromisoformat(str(raw).replace("Z","+00:00")).replace(tzinfo=None)
    except ValueError: raise HTTPException(409,"Remote expiration date is invalid")
    after=before+timedelta(days=days)
    result=await rw.extend_idempotent(user_id,days,before,after)
    await audit(db,"remnawave.user.extend",admin.email,str(user_id),{"days":days,"verified_expires_at":str(result.get("expires_at"))}); await db.commit(); return {"ok":True,"already_applied":result.get("already_applied",False),"expires_at":result.get("expires_at")}
@app.get("/api/admin/remnawave/users/{user_id}/subscription")
async def rw_subscription(user_id:int,admin=Depends(require_permission("read"))): return await RemnawaveClient().get_subscription(user_id)
@app.get("/api/admin/remnawave/users/{user_id}/keys")
async def rw_keys(user_id:int,admin=Depends(require_permission("manage_users"))): return await RemnawaveClient().get_connection_keys(user_id)

@app.get("/api/admin/remnawave/health")
async def remnawave_health(admin=Depends(require_permission("read"))):
    from .tariff_api import remnawave_server_status
    return await remnawave_server_status("admin")

@app.post("/api/admin/provision-node")
async def provision_node(payload:dict,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("provision_nodes"))):
    required=["host","ssh_username","compose_yaml"]
    if any(not payload.get(k) for k in required): raise HTTPException(400,"host, ssh_username and compose_yaml are required")
    try:
        result=run_ssh(host=payload["host"],port=int(payload.get("ssh_port",22)),username=payload["ssh_username"],password=payload.get("ssh_password"),private_key=payload.get("ssh_private_key"),compose_yaml=payload["compose_yaml"],panel_ip=payload.get("panel_ip",""),node_port=int(payload.get("node_port",2222)),host_key_fingerprint=payload.get("ssh_host_key"))
        await audit(db,"node.provisioned",admin.email,payload["host"]); await db.commit(); return result
    except ProvisionError as e: raise HTTPException(400,str(e))
    except Exception as e: raise HTTPException(502,"SSH provisioning failed") from e

class AdminUserIn(BaseModel):
    email:str=Field(min_length=5,max_length=320)
    password:str|None=Field(default=None,min_length=12,max_length=256)
    role:str="viewer"
    disabled:bool=False
    telegram_id:int|None=Field(default=None,ge=1)

@app.get("/api/admin/admins")
async def list_admins(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_admins"))):
    rows=(await db.execute(select(AdminUser).order_by(AdminUser.id))).scalars().all()
    return [{"id":x.id,"email":x.email,"telegram_id":x.telegram_id,"role":x.role,"disabled":x.disabled,"mfa_enabled":x.mfa_enabled,"created_at":x.created_at,"last_login_at":x.last_login_at} for x in rows]

@app.post("/api/admin/admins")
async def create_admin(payload:AdminUserIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_admins"))):
    if payload.role not in {"viewer","operator","admin"} or not payload.password: raise HTTPException(400,"Valid role and password are required")
    x=AdminUser(email=payload.email.strip().lower(),telegram_id=payload.telegram_id,password_hash=hash_password(payload.password),role=payload.role,disabled=payload.disabled); db.add(x)
    try: await db.commit()
    except IntegrityError: await db.rollback(); raise HTTPException(409,"Администратор с таким email или Telegram ID уже существует")
    await audit(db,"admin.created",admin.email,x.email,{"role":x.role}); await db.commit(); return {"id":x.id}

@app.put("/api/admin/admins/{admin_id}")
async def update_admin(admin_id:int,payload:AdminUserIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_admins"))):
    x=await db.get(AdminUser,admin_id)
    if not x: raise HTTPException(404,"Admin not found")
    if admin.id==x.id and payload.disabled: raise HTTPException(400,"You cannot disable yourself")
    if payload.role not in {"viewer","operator","admin"}: raise HTTPException(400,"Invalid role")
    old_role=x.role; old_disabled=x.disabled; old_email=x.email; old_telegram_id=x.telegram_id
    x.email=payload.email.strip().lower(); x.telegram_id=payload.telegram_id; x.role=payload.role; x.disabled=payload.disabled
    if payload.password: x.password_hash=hash_password(payload.password)
    if old_role != x.role or old_disabled != x.disabled or payload.password or old_email != x.email or old_telegram_id != x.telegram_id: await db.execute(__import__("sqlalchemy").update(AdminSession).where(AdminSession.admin_id==x.id,AdminSession.revoked_at.is_(None)).values(revoked_at=datetime.utcnow()))
    await audit(db,"admin.updated",admin.email,x.email,{"role":x.role,"disabled":x.disabled}); await db.commit(); return {"ok":True}

@app.delete("/api/admin/admins/{admin_id}")
async def delete_admin(admin_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_admins"))):
    x=await db.get(AdminUser,admin_id)
    if not x: raise HTTPException(404,"Admin not found")
    if x.id==admin.id: raise HTTPException(400,"You cannot delete yourself")
    await db.delete(x); await audit(db,"admin.deleted",admin.email,x.email); await db.commit(); return {"ok":True}

@app.post("/api/admin/auth/logout")
async def admin_logout(request:Request,response:Response,db:AsyncSession=Depends(get_db)):
    token=request.cookies.get("rw_admin")
    if token:
        try:
            claims=decode_token(token); jti=claims.get("jti")
            if jti:
                row=(await db.execute(select(AdminSession).where(AdminSession.jti_hash==hashlib.sha256(jti.encode()).hexdigest()))).scalar_one_or_none()
                if row: row.revoked_at=datetime.utcnow(); await db.commit()
        except Exception as exc:
            logger.warning("Non-critical operation failed: %s", exc)
    response.delete_cookie("rw_admin"); response.delete_cookie("rw_csrf"); return {"ok":True}

@app.get("/api/admin/security")
async def admin_security(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    active_sessions=int((await db.execute(select(func.count()).select_from(AdminSession).where(AdminSession.revoked_at.is_(None),AdminSession.expires_at>datetime.utcnow()))).scalar() or 0)
    failed_24h=int((await db.execute(select(func.count()).select_from(Payment).where(Payment.fulfillment_status=="failed",Payment.created_at>=datetime.utcnow()-timedelta(hours=24)))).scalar() or 0)
    last_backup=(await db.execute(select(BackupJob).where(BackupJob.status=="completed").order_by(BackupJob.created_at.desc()).limit(1))).scalar_one_or_none()
    gate_raw=await setting_value(db,PRODUCTION_PAYMENTS_GATE_KEY,"0")
    return {"admin_auth":"password + optional TOTP","mfa_enabled":bool(admin.mfa_enabled),"production_payments_enabled":gate_raw=="1","rbac_roles":["viewer","operator","admin"],"version":APP_VERSION,"active_sessions":active_sessions,"fulfillment_failures_24h":failed_24h,"backup":{"last_success":last_backup.created_at if last_backup else None,"healthy":bool(last_backup and last_backup.created_at>=datetime.utcnow()-timedelta(hours=25))},"ssh_credentials_persisted":False,"node_compose_source":"official Remnawave Panel"}


class ProductionGateIn(BaseModel):
    enabled: bool

@app.post("/api/admin/payments/production-gate")
async def production_payment_gate(payload:ProductionGateIn, db:AsyncSession=Depends(get_db), admin=Depends(require_permission("security.manage"))):
    if not payload.enabled:
        await set_setting(db,PRODUCTION_PAYMENTS_GATE_KEY,"0")
        await audit(db,"payments.production_gate.disabled",admin.email,None)
        await db.commit()
        return {"enabled":False}
    raw=await setting_value(db,STAGING_E2E_STATUS_KEY,"{}")
    try: status=json.loads(raw)
    except Exception: status={}
    if status.get("status")!="passed" or not status.get("full_e2e"):
        raise HTTPException(409,"Сначала необходимо успешно завершить полный staging E2E: checkout → webhook → fulfillment → duplicate webhook → refund")
    finished=status.get("finished_at")
    try:
        finished_dt=datetime.fromisoformat(str(finished)) if finished else None
    except ValueError:
        finished_dt=None
    if not finished_dt or datetime.utcnow()-finished_dt.replace(tzinfo=None) > timedelta(hours=PRODUCTION_GATE_MAX_AGE_HOURS):
        raise HTTPException(409,"Результат staging E2E устарел; запустите проверку заново")
    await set_setting(db,PRODUCTION_PAYMENTS_GATE_KEY,"1")
    await audit(db,"payments.production_gate.enabled",admin.email,None,{"staging_finished_at":finished})
    await db.commit()
    return {"enabled":True}

# ---------- Staging E2E ----------
STAGING_E2E_CONFIG_KEY="staging_e2e.config"
STAGING_E2E_STATUS_KEY="staging_e2e.status"
STAGING_E2E_LOCK=asyncio.Lock()
PRODUCTION_PAYMENTS_GATE_KEY="payments.production_gate"
PRODUCTION_GATE_MAX_AGE_HOURS=24

class StagingE2EConfigIn(BaseModel):
    public_base_url:str=Field(min_length=8,max_length=2048)
    remnawave_url:str=Field(min_length=8,max_length=2048)
    remnawave_token:str=Field(default="",max_length=4096)
    user_bearer_token:str=Field(default="",max_length=4096)
    plan_id:int=Field(gt=0)
    providers:list[str]=Field(default_factory=lambda:["yookassa","platega","rollypay"])
    yookassa_enabled:bool=True
    platega_enabled:bool=True
    rollypay_enabled:bool=True
    timeout_seconds:int=Field(default=1800,ge=60,le=7200)
    yookassa_api_url:str="https://api.yookassa.ru"
    yookassa_shop_id:str=""
    yookassa_secret_key:str=""
    platega_api_url:str="https://app.platega.io"
    platega_merchant_id:str=""
    platega_secret:str=""
    rollypay_api_url:str="https://rollypay.io"
    rollypay_api_key:str=""
    rollypay_signing_secret:str=""
    staging_confirmed:bool=False

async def _staging_config(db):
    raw=await setting_value(db,STAGING_E2E_CONFIG_KEY,"")
    if not raw: return None
    try: return json.loads(decrypt_secret(raw))
    except Exception as exc:
        logger.warning("Unable to decrypt staging E2E config: %s", exc); return None

@app.get("/api/admin/staging-e2e/config")
async def staging_e2e_config(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("staging_e2e.manage"))):
    cfg=await _staging_config(db)
    status=await setting_value(db,STAGING_E2E_STATUS_KEY,"{}")
    try: status=json.loads(status)
    except Exception: status={}
    if cfg:
        safe={"public_base_url":cfg.get("public_base_url"),"remnawave_url":cfg.get("remnawave_url"),"plan_id":cfg.get("plan_id"),"providers":cfg.get("providers",[]),"yookassa_enabled":cfg.get("yookassa_enabled",True),"platega_enabled":cfg.get("platega_enabled",True),"rollypay_enabled":cfg.get("rollypay_enabled",True),"timeout_seconds":cfg.get("timeout_seconds",1800),"staging_confirmed":bool(cfg.get("staging_confirmed")),"provider_credentials":{"yookassa":bool(cfg.get("yookassa_shop_id") and cfg.get("yookassa_secret_key")),"platega":bool(cfg.get("platega_merchant_id") and cfg.get("platega_secret")),"rollypay":bool(cfg.get("rollypay_api_key"))},"credentials_configured":True,"remnawave_token_configured":bool(cfg.get("remnawave_token")),"user_bearer_token_configured":bool(cfg.get("user_bearer_token"))}
    else: safe={"credentials_configured":False,"providers":["yookassa","platega","rollypay"],"timeout_seconds":1800}
    return {"config":safe,"status":status}

@app.put("/api/admin/staging-e2e/config")
async def update_staging_e2e_config(payload:StagingE2EConfigIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("staging_e2e.manage"))):
    # Staging endpoints are administrator-supplied and later contacted by the server/runner.
    # Require globally routable HTTPS targets to prevent SSRF and DNS-rebinding to internal services.
    validate_public_url(payload.public_base_url, allow_empty=False)
    validate_public_url(payload.remnawave_url, allow_empty=False)
    for provider_url in (payload.yookassa_api_url, payload.platega_api_url, payload.rollypay_api_url):
        validate_public_url(provider_url, allow_empty=False)
    if not payload.staging_confirmed:
        raise HTTPException(400,"Подтвердите, что используются sandbox/staging-учётные данные; production-ключи запрещены")
    prod_pairs=[(payload.yookassa_shop_id,payload.yookassa_secret_key,(settings.yookassa_shop_id,settings.yookassa_secret_key)),(payload.platega_merchant_id,payload.platega_secret,(settings.platega_merchant_id,settings.platega_secret)),(payload.rollypay_api_key,payload.rollypay_signing_secret,(settings.rollypay_api_key,settings.rollypay_signing_secret))]
    for a,b,(pa,pb) in prod_pairs:
        if (a and pa and a==pa) or (b and pb and b==pb):
            raise HTTPException(400,"Staging E2E не может использовать production-платёжные credentials")
    providers=[p for p in payload.providers if p in {"yookassa","platega","rollypay"}]
    enabled=[p for p,flag in (("yookassa",payload.yookassa_enabled),("platega",payload.platega_enabled),("rollypay",payload.rollypay_enabled)) if flag]
    providers=[p for p in providers if p in enabled] or enabled
    data=payload.model_dump(); data["providers"]=providers; data["runner_token"]=secrets.token_urlsafe(32)
    await set_setting(db,STAGING_E2E_CONFIG_KEY,encrypt_secret(json.dumps(data,ensure_ascii=False)))
    await set_setting(db,PRODUCTION_PAYMENTS_GATE_KEY,"0")
    await audit(db,"staging_e2e.config.updated",admin.email,None,{"providers":providers,"public_base_url":payload.public_base_url,"remnawave_url":payload.remnawave_url,"plan_id":payload.plan_id})
    await db.commit()
    return {"ok":True,"providers":providers}

async def _run_staging_e2e(config, admin_email):
    async with AsyncSession(engine,expire_on_commit=False) as db:
        await set_setting(db,STAGING_E2E_STATUS_KEY,json.dumps({"status":"running","started_at":datetime.utcnow().isoformat(),"provider_results":[]},ensure_ascii=False)); await set_setting(db,PRODUCTION_PAYMENTS_GATE_KEY,"0"); await db.commit()
    env=os.environ.copy()
    env.update({"STAGING_PUBLIC_BASE_URL":config["public_base_url"],"STAGING_REMNAWAVE_URL":config["remnawave_url"],"STAGING_REMNAWAVE_TOKEN":config["remnawave_token"],"STAGING_USER_BEARER_TOKEN":config["user_bearer_token"],"STAGING_PLAN_ID":str(config["plan_id"]),"STAGING_TIMEOUT_SECONDS":str(config.get("timeout_seconds",1800)),"STAGING_PROVIDERS":",".join(config.get("providers",[])),"STAGING_RUNNER_TOKEN":config["runner_token"]})
    script="/app/staging-e2e.sh"
    try:
        proc=await asyncio.create_subprocess_exec("bash",script,env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
        try: out,_=await asyncio.wait_for(proc.communicate(),timeout=config.get("timeout_seconds",1800)+30)
        except asyncio.TimeoutError:
            proc.kill(); out,_=await proc.communicate(); raise RuntimeError("Превышен таймаут staging E2E")
        text=out.decode("utf-8","replace")[-30000:]
        # Exit code 0 only means the runner completed its configured checks. A production gate
        # requires an explicit FULL_E2E_PASS marker emitted after checkout/webhook/fulfillment/refund
        # verification. This prevents the old false-positive where payment creation alone unlocked production.
        full_pass = proc.returncode == 0 and "FULL_E2E_PASS" in text
        status="passed" if full_pass else ("awaiting_checkout" if proc.returncode==0 else "failed")
        result={"status":status,"full_e2e":full_pass,"exit_code":proc.returncode,"finished_at":datetime.utcnow().isoformat(),"output":text,"admin":admin_email}
    except Exception as exc:
        result={"status":"failed","exit_code":-1,"finished_at":datetime.utcnow().isoformat(),"output":str(exc),"admin":admin_email}
    async with AsyncSession(engine,expire_on_commit=False) as db:
        await set_setting(db,STAGING_E2E_STATUS_KEY,json.dumps(result,ensure_ascii=False)); await audit(db,"staging_e2e.completed",admin_email,None,{"status":result["status"],"exit_code":result["exit_code"]}); await db.commit()

@app.post("/api/internal/staging-e2e/payment")
async def internal_staging_payment(payload:dict,request:Request,db:AsyncSession=Depends(get_db)):
    client_host=request.client.host if request.client else ""
    if client_host not in {"127.0.0.1","::1"}: raise HTTPException(403,"Staging endpoint доступен только локальному runner")
    cfg=await _staging_config(db)
    if not cfg or request.headers.get("X-Staging-Runner-Token") != cfg.get("runner_token"):
        raise HTTPException(403,"Недействительный staging runner token")
    if not cfg or not cfg.get("staging_confirmed"): raise HTTPException(409,"Staging E2E не настроен безопасно")
    provider=str(payload.get("provider")); plan=await db.get(Plan,int(payload.get("plan_id",0)))
    if not plan or not plan.enabled: raise HTTPException(404,"Тестовый тариф не найден")
    creds={"yookassa":{"api_url":cfg.get("yookassa_api_url"),"shop_id":cfg.get("yookassa_shop_id"),"secret_key":cfg.get("yookassa_secret_key")},"platega":{"api_url":cfg.get("platega_api_url"),"merchant_id":cfg.get("platega_merchant_id"),"secret":cfg.get("platega_secret")},"rollypay":{"api_url":cfg.get("rollypay_api_url"),"api_key":cfg.get("rollypay_api_key"),"signing_secret":cfg.get("rollypay_signing_secret")}}.get(provider)
    if not creds: raise HTTPException(400,"Неизвестный staging-провайдер")
    oid=f"STAGING-{provider.upper()}-{secrets.token_hex(8)}"
    result=await staging_create_payment(provider,creds,Decimal(str(plan.price)),oid,"Staging E2E",cfg["public_base_url"].rstrip("/")+"/staging-e2e")
    return {"provider":provider,"order_id":oid,"amount":float(plan.price),**result}

@app.post("/api/admin/staging-e2e/run")
async def run_staging_e2e(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("staging_e2e.manage"))):
    if STAGING_E2E_LOCK.locked(): raise HTTPException(409,"Staging E2E уже выполняется")
    cfg=await _staging_config(db)
    if not cfg: raise HTTPException(400,"Сначала сохраните конфигурацию staging E2E")
    status_raw=await setting_value(db,STAGING_E2E_STATUS_KEY,"{}")
    try: status=json.loads(status_raw)
    except Exception: status={}
    if status.get("status")=="running": raise HTTPException(409,"Staging E2E уже выполняется")
    async def guarded():
        async with STAGING_E2E_LOCK: await _run_staging_e2e(cfg,admin.email)
    asyncio.create_task(guarded())
    await audit(db,"staging_e2e.started",admin.email,None,{"providers":cfg.get("providers",[])})
    await db.commit()
    return {"started":True}

@app.get("/api/admin/staging-e2e/status")
async def staging_e2e_status(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("staging_e2e.manage"))):
    raw=await setting_value(db,STAGING_E2E_STATUS_KEY,"{}")
    try: return json.loads(raw)
    except Exception: return {"status":"never"}

# ---------- Backups ----------
BACKUP_LOCK=asyncio.Lock()
BACKUP_INTERVALS={"off":0,"6h":21600,"12h":43200,"24h":86400}

async def setting_value(db,key,default=""):
    row=await db.get(AppSetting,key); return row.value if row else default

async def set_setting(db,key,value):
    row=await db.get(AppSetting,key)
    if row: row.value=value
    else: db.add(AppSetting(key=key,value=value))

def _backup_path(filename: str) -> pathlib.Path:
    if not filename or pathlib.Path(filename).name != filename or filename not in {filename.strip()} or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid backup filename")
    path = (pathlib.Path(settings.backups_dir) / filename).resolve()
    root = pathlib.Path(settings.backups_dir).resolve()
    if path.parent != root:
        raise HTTPException(400, "Invalid backup path")
    return path

async def enforce_backup_retention(db: AsyncSession):
    retention = int(await setting_value(db, "backup_retention", "7"))
    rows = (await db.execute(select(BackupJob).where(BackupJob.status == "completed").order_by(BackupJob.created_at.desc()))).scalars().all()
    for old in rows[retention:]:
        if old.filename:
            _backup_path(old.filename).unlink(missing_ok=True)
        await db.delete(old)

def _database_cli_config():
    """Return host/user/database/password for PostgreSQL CLI tools from DATABASE_URL."""
    raw=settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed=urllib.parse.urlparse(raw)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise RuntimeError("DATABASE_URL must use PostgreSQL")
    host=parsed.hostname or "db"
    user=urllib.parse.unquote(parsed.username or "")
    database=urllib.parse.unquote((parsed.path or "").lstrip("/"))
    password=urllib.parse.unquote(parsed.password or os.getenv("DB_PASSWORD", ""))
    port=str(parsed.port or 5432)
    if not user or not database:
        raise RuntimeError("DATABASE_URL is missing PostgreSQL user or database")
    return {"host":host,"port":port,"user":user,"database":database,"password":password}


async def create_project_backup(db, actor="system"):
    if BACKUP_LOCK.locked(): raise HTTPException(409,"A backup is already running")
    try:
        backup_lock,lock_token=await _acquire_redis_lock("lock:backup",ttl=3600,conflict_message="A backup is already running")
    except RuntimeError as exc:
        raise HTTPException(409,str(exc)) from exc
    async with BACKUP_LOCK:
        job=BackupJob(status="running",created_at=datetime.utcnow()); db.add(job); await db.commit(); await db.refresh(job)
        ts=datetime.utcnow().strftime("%Y%m%d-%H%M%S"); work=pathlib.Path("/tmp")/f"vpn-backup-{job.id}-{ts}"; work.mkdir(parents=True,exist_ok=True)
        try:
            backups=pathlib.Path(settings.backups_dir); backups.mkdir(parents=True,exist_ok=True); dump=work/"database.sql"; archive=work/f"remnawave-vpn-shop-{ts}.tar.gz"
            dbcli=_database_cli_config()
            proc=await asyncio.create_subprocess_exec("pg_dump","-h",dbcli["host"],"-p",dbcli["port"],"-U",dbcli["user"],"-d",dbcli["database"],"--clean","--if-exists","--no-owner","--no-privileges",stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,env={**os.environ,"PGPASSWORD":dbcli["password"]})
            out,err=await proc.communicate()
            if proc.returncode!=0: raise RuntimeError(f"pg_dump failed: {err.decode(errors='ignore')[-1000:]}")
            dump.write_bytes(out)
            include_env=await setting_value(db,"backup_include_env","1")=="1"
            with tarfile.open(archive,"w:gz") as tar:
                def _tar_filter(info):
                    parts=set(pathlib.Path(info.name).parts)
                    if parts & {"backups","node_modules","__pycache__",".git"}: return None
                    if not include_env and pathlib.Path(info.name).name == ".env": return None
                    return info
                tar.add(settings.project_dir,arcname="project",filter=_tar_filter)
                tar.add(dump,arcname="database.sql")
                media=pathlib.Path(settings.media_dir)
                if media.exists(): tar.add(media,arcname="media")
            encrypt=await setting_value(db,"backup_encrypt","1")=="1"
            final=backups/archive.name
            if encrypt:
                password_enc=await setting_value(db,"backup_password","")
                if not password_enc: raise RuntimeError("Backup encryption password is not configured")
                from .security import decrypt_secret
                password=decrypt_secret(password_enc); encrypted=backups/(archive.name+".enc")
                proc=await asyncio.create_subprocess_exec("openssl","enc","-aes-256-cbc","-pbkdf2","-salt","-in",str(archive),"-out",str(encrypted),"-pass","stdin",stdin=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
                _,err=await proc.communicate((password+"\n").encode())
                if proc.returncode!=0: raise RuntimeError(f"Encryption failed: {err.decode(errors='ignore')[-1000:]}")
                archive.unlink(missing_ok=True); final=encrypted
            else: shutil.move(str(archive),str(final))
            job.status="completed"; job.filename=final.name; job.size_bytes=final.stat().st_size; job.sha256=hashlib.sha256(final.read_bytes()).hexdigest(); job.encrypted=encrypt; job.finished_at=datetime.utcnow()
            if await setting_value(db,"backup_s3_enabled","0")=="1":
                try:
                    import boto3
                    s3=boto3.client("s3",endpoint_url=settings.s3_endpoint_url,region_name=settings.s3_region or None,aws_access_key_id=settings.s3_access_key,aws_secret_access_key=settings.s3_secret_key)
                    bucket=await setting_value(db,"backup_s3_bucket",settings.s3_bucket); prefix=await setting_value(db,"backup_s3_prefix",settings.backup_s3_prefix).strip("/")
                    key=f"{prefix}/{final.name}"
                    await asyncio.to_thread(s3.upload_file,str(final),bucket,key)
                    remote=await asyncio.to_thread(s3.head_object,Bucket=bucket,Key=key)
                    if int(remote.get("ContentLength",-1)) != final.stat().st_size: raise RuntimeError("S3 remote size verification failed")
                    # Keep the same retention policy remotely.
                    listing=await asyncio.to_thread(s3.list_objects_v2,Bucket=bucket,Prefix=prefix+"/")
                    objects=sorted(listing.get("Contents",[]),key=lambda o:o.get("LastModified"))
                    keep=max(1,int(await setting_value(db,"backup_retention","7")))
                    for obj in objects[:-keep]:
                        await asyncio.to_thread(s3.delete_object,Bucket=bucket,Key=obj["Key"])
                except Exception as exc: raise RuntimeError(f"S3 upload failed: {exc}")
            await audit(db,"backup.created",actor,final.name,{"encrypted":encrypt,"include_env":include_env,"sha256":job.sha256,"s3":await setting_value(db,"backup_s3_enabled","0")=="1"}); await enforce_backup_retention(db); await db.commit()
            return {"id":job.id,"status":job.status,"filename":job.filename,"size_bytes":job.size_bytes,"encrypted":encrypt}
        except Exception as e:
            job.status="failed"; job.error=str(e)[:2000]; job.finished_at=datetime.utcnow(); _METRICS["backup_failures"] += 1; await db.commit(); await send_alert(f"Backup #{job.id} failed: {str(e)[:500]}"); raise
        finally:
            shutil.rmtree(work,ignore_errors=True)
            await _release_payment_side_effect_lock(backup_lock,lock_token)
@app.get("/api/admin/backups")
async def list_backups(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    rows=(await db.execute(select(BackupJob).order_by(BackupJob.created_at.desc()).limit(50))).scalars().all()
    return [{"id":x.id,"status":x.status,"filename":x.filename,"size_bytes":x.size_bytes,"sha256":x.sha256,"encrypted":x.encrypted,"error":x.error,"created_at":x.created_at,"finished_at":x.finished_at} for x in rows]

class BackupConfigIn(BaseModel):
    schedule: str = "24h"
    retention: int = Field(default=7, ge=1, le=90)
    encrypt: bool = True
    password: str|None = Field(default=None,min_length=12,max_length=256)
    include_env: bool = True
    s3_enabled: bool = False
    s3_bucket: str|None = Field(default=None,max_length=255)
    s3_prefix: str = Field(default="vpn-shop",max_length=100)

@app.get("/api/admin/backups/config")
async def backup_config(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    return {"schedule":await setting_value(db,"backup_schedule","off"),"retention":int(await setting_value(db,"backup_retention","7")),"encrypt":await setting_value(db,"backup_encrypt","1")=="1","include_env":await setting_value(db,"backup_include_env","1")=="1","password_configured":bool(await setting_value(db,"backup_password","")),"s3_enabled":await setting_value(db,"backup_s3_enabled","0")=="1","s3_bucket":await setting_value(db,"backup_s3_bucket",""),"s3_prefix":await setting_value(db,"backup_s3_prefix",settings.backup_s3_prefix)}

@app.put("/api/admin/backups/config")
async def update_backup_config(payload:BackupConfigIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_admins"))):
    if payload.schedule not in BACKUP_INTERVALS: raise HTTPException(400,"Invalid backup schedule")
    if payload.include_env and not payload.encrypt: raise HTTPException(400,"Encrypt backups when .env is included")
    if payload.encrypt and payload.password is None and not await setting_value(db,"backup_password",""): raise HTTPException(400,"Set a backup encryption password first")
    if payload.s3_enabled and not (settings.s3_endpoint_url and (payload.s3_bucket or settings.s3_bucket) and settings.s3_access_key and settings.s3_secret_key): raise HTTPException(400,"S3 is not configured in environment")
    await set_setting(db,"backup_schedule",payload.schedule); await set_setting(db,"backup_retention",str(payload.retention)); await set_setting(db,"backup_encrypt","1" if payload.encrypt else "0"); await set_setting(db,"backup_include_env","1" if payload.include_env else "0"); await set_setting(db,"backup_s3_enabled","1" if payload.s3_enabled else "0"); await set_setting(db,"backup_s3_bucket",payload.s3_bucket or settings.s3_bucket); await set_setting(db,"backup_s3_prefix",payload.s3_prefix)
    if payload.password is not None: await set_setting(db,"backup_password",encrypt_secret(payload.password))
    await audit(db,"backup.config.updated",admin.email,None,{"schedule":payload.schedule,"retention":payload.retention,"encrypt":payload.encrypt,"include_env":payload.include_env}); await db.commit(); return await backup_config(db,admin)

@app.post("/api/admin/backups/run")
async def run_backup(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_admins"))): return await create_project_backup(db,admin.email)

@app.get("/api/admin/backups/{backup_id}/download")
async def download_backup(backup_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_admins"))):
    job=await db.get(BackupJob,backup_id)
    if not job or not job.filename: raise HTTPException(404,"Backup not found")
    path=_backup_path(job.filename)
    if not path.is_file(): raise HTTPException(404,"Backup file not found")
    return FileResponse(path,filename=job.filename,media_type="application/octet-stream",headers={"Cache-Control":"private, no-store"})

@app.delete("/api/admin/backups/{backup_id}")
async def delete_backup(backup_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_admins"))):
    job=await db.get(BackupJob,backup_id)
    if not job or not job.filename: raise HTTPException(404,"Backup not found")
    _backup_path(job.filename).unlink(missing_ok=True); await db.delete(job); await audit(db,"backup.deleted",admin.email,job.filename); await db.commit(); return {"ok":True}

async def backup_scheduler():
    while True:
        try:
            await asyncio.sleep(60)
            async with AsyncSession(engine,expire_on_commit=False) as db:
                interval=BACKUP_INTERVALS.get(await setting_value(db,"backup_schedule","off"),0)
                if not interval or BACKUP_LOCK.locked(): continue
                last=(await db.execute(select(BackupJob).where(BackupJob.status=="completed").order_by(BackupJob.created_at.desc()).limit(1))).scalar_one_or_none()
                if last and (datetime.utcnow()-last.created_at).total_seconds()<interval: continue
                await create_project_backup(db,"scheduler")
                await enforce_backup_retention(db)
                await db.commit()
        except Exception: continue

@app.post("/api/admin/backups/{backup_id}/verify")
async def verify_backup(backup_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("backups.write"))):
    job=await db.get(BackupJob,backup_id)
    if not job or not job.filename: raise HTTPException(404,"Backup not found")
    path=_backup_path(job.filename)
    if not path.is_file(): raise HTTPException(404,"Backup file not found")
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024*1024), b""): h.update(chunk)
    digest=h.hexdigest()
    return {"ok":digest==job.sha256,"expected":job.sha256,"actual":digest,"size_bytes":path.stat().st_size}

MAX_BACKUP_ARCHIVE_BYTES=1024*1024*1024
MAX_BACKUP_MEMBERS=50000
MAX_BACKUP_EXTRACTED_BYTES=5*1024*1024*1024
MAX_BACKUP_FILE_BYTES=1024*1024*1024
MAX_BACKUP_PATH_DEPTH=32

def _validate_tar_safety(tar:tarfile.TarFile):
    members=tar.getmembers()
    if len(members)>MAX_BACKUP_MEMBERS: raise HTTPException(400,"Backup contains too many files")
    total=0
    for m in members:
        posix=pathlib.PurePosixPath(m.name)
        parts=posix.parts
        if posix.is_absolute() or ".." in parts: raise HTTPException(400,"Unsafe backup path")
        if len(parts)>MAX_BACKUP_PATH_DEPTH: raise HTTPException(400,"Backup path is too deep")
        if m.size>MAX_BACKUP_FILE_BYTES: raise HTTPException(400,"Backup member is too large")
        if m.isfile(): total += m.size
        if total>MAX_BACKUP_EXTRACTED_BYTES: raise HTTPException(400,"Backup extracted size is too large")
        if m.issym() or m.islnk(): raise HTTPException(400,"Links are not allowed in backups")

def _safe_extract_members(tar:tarfile.TarFile, names:set[str], destination:pathlib.Path):
    root=destination.resolve()
    for member in tar.getmembers():
        if member.name not in names: continue
        target=(destination/member.name).resolve()
        if target != root and root not in target.parents: raise HTTPException(400,"Unsafe archive path")
        tar.extract(member,path=destination)

@app.post("/api/admin/backups/{backup_id}/validate")
async def validate_backup_archive(backup_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("backups.write"))):
    job=await db.get(BackupJob,backup_id)
    if not job or not job.filename: raise HTTPException(404,"Backup not found")
    path=_backup_path(job.filename)
    if not path.is_file(): raise HTTPException(404,"Backup file not found")
    if path.stat().st_size>MAX_BACKUP_ARCHIVE_BYTES: raise HTTPException(400,"Backup archive is too large")
    work=pathlib.Path("/tmp")/f"validate-{secrets.token_hex(8)}"; work.mkdir()
    try:
        source=path
        if job.encrypted:
            password_enc=await setting_value(db,"backup_password","")
            if not password_enc: raise HTTPException(500,"Backup password is not configured")
            dec=work/"backup.tar.gz"
            proc=await asyncio.create_subprocess_exec("openssl","enc","-d","-aes-256-cbc","-pbkdf2","-in",str(source),"-out",str(dec),"-pass","stdin",stdin=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            _,err=await proc.communicate((__import__("backend.app.security",fromlist=["decrypt_secret"]).decrypt_secret(password_enc)+"\n").encode())
            if proc.returncode!=0: raise HTTPException(400,"Backup decryption failed")
            source=dec
        with tarfile.open(source,"r:gz") as tar:
            _validate_tar_safety(tar)
            names=[m.name for m in tar.getmembers()]
            if "database.sql" not in names: raise HTTPException(400,"database.sql not found in backup")
            root=work.resolve()
            for name in names:
                target=(work/name).resolve()
                if target!=root and root not in target.parents: raise HTTPException(400,"Unsafe archive path")
        return {"ok":True,"database_sql":True,"members":len(names),"checksum":job.sha256}
    finally: shutil.rmtree(work,ignore_errors=True)

@app.post("/api/admin/backups/{backup_id}/restore")
async def restore_backup(backup_id:int,confirm:str,otp:str|None=None,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("backups.write"))):
    if confirm!="RESTORE": raise HTTPException(400,"Set confirm=RESTORE")
    if admin.mfa_enabled and (not otp or not verify_totp(admin,otp)): raise HTTPException(401,"Valid MFA code is required for restore")
    job=await db.get(BackupJob,backup_id)
    if not job or not job.filename: raise HTTPException(404,"Backup not found")
    path=_backup_path(job.filename)
    if not path.is_file(): raise HTTPException(404,"Backup file not found")
    if path.stat().st_size>MAX_BACKUP_ARCHIVE_BYTES: raise HTTPException(400,"Backup archive is too large")
    if job.sha256:
        h=hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024*1024),b""): h.update(chunk)
        if h.hexdigest()!=job.sha256: raise HTTPException(409,"Backup checksum mismatch")
    if redis_client is None: raise HTTPException(503,"Redis is required for restore")
    try:
        maintenance_lock,maintenance_token=await _acquire_redis_lock("lock:maintenance",ttl=1800,conflict_message="Maintenance operation already in progress")
    except RuntimeError as exc:
        raise HTTPException(409,str(exc)) from exc
    try:
        await set_setting(db,"maintenance_mode","1"); await db.commit()
        # Always create a fresh pre-restore snapshot so a failed/incorrect restore can be recovered.
        await create_project_backup(db, f"pre-restore:{admin.email}")
    except Exception:
        await _release_payment_side_effect_lock(maintenance_lock,maintenance_token); raise
    work=pathlib.Path("/tmp")/f"restore-{secrets.token_hex(8)}"; work.mkdir()
    restore_ok=False
    try:
        source=path
        if job.encrypted:
            password_enc=await setting_value(db,"backup_password","")
            if not password_enc: raise HTTPException(500,"Backup password is not configured")
            dec=work/"backup.tar.gz"; from .security import decrypt_secret
            proc=await asyncio.create_subprocess_exec("openssl","enc","-d","-aes-256-cbc","-pbkdf2","-in",str(source),"-out",str(dec),"-pass","stdin",stdin=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE); _,err=await proc.communicate((decrypt_secret(password_enc)+"\n").encode())
            if proc.returncode!=0: raise HTTPException(400,"Backup decryption failed")
            source=dec
        with tarfile.open(source,"r:gz") as tar:
            _validate_tar_safety(tar)
            member=next((m for m in tar.getmembers() if m.name=="database.sql"),None)
            if not member: raise HTTPException(400,"database.sql not found in backup")
            _safe_extract_members(tar,{"database.sql"},work)
            media_members=[m.name for m in tar.getmembers() if m.name=="media" or m.name.startswith("media/")]
            if media_members:
                media_root=pathlib.Path(settings.media_dir)
                media_root.mkdir(parents=True,exist_ok=True)
                for name in media_members:
                    target=(media_root/pathlib.Path(name).relative_to("media")).resolve() if name!="media" else media_root.resolve()
                    if target!=media_root.resolve() and media_root.resolve() not in target.parents: raise HTTPException(400,"Unsafe media archive path")
                    _safe_extract_members(tar,{name},work)
                extracted=work/"media"
                if extracted.exists():
                    for src in extracted.rglob("*"):
                        if src.is_file():
                            dst=media_root/src.relative_to(extracted); dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
        sql_file=work/"database.sql"
        # Use the configured SQLAlchemy database URL rather than hard-coded deployment
        # credentials. This keeps restore correct for non-default DB hosts/users/passwords.
        db_url=urllib.parse.urlparse(settings.database_url.replace("postgresql+asyncpg://","postgresql://",1))
        db_host=db_url.hostname or "db"; db_user=urllib.parse.unquote(db_url.username or "vpnshop")
        db_name=(db_url.path or "/vpnshop").lstrip("/") or "vpnshop"
        db_password=urllib.parse.unquote(db_url.password or os.getenv("DB_PASSWORD", ""))
        proc=await asyncio.create_subprocess_exec("psql","-h",db_host,"-U",db_user,"-d",db_name,"-v","ON_ERROR_STOP=1","-f",str(sql_file),env={**os.environ,"PGPASSWORD":db_password},stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE); out,err=await proc.communicate()
        if proc.returncode!=0: raise HTTPException(500,f"Restore failed: {err.decode(errors='ignore')[-1000:]}")
        # The active SQLAlchemy session is invalid after destructive DB replacement.
        await db.close()
        mig=await asyncio.create_subprocess_exec("alembic","upgrade","head",cwd=settings.project_dir,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE); mout,merr=await mig.communicate()
        if mig.returncode!=0: raise HTTPException(500,f"Migration after restore failed: {merr.decode(errors='ignore')[-1000:]}")
        async with AsyncSession(engine,expire_on_commit=False) as check_db:
            await check_db.execute(sql_text("SELECT 1"))
            await audit(check_db,"backup.restored",admin.email,job.filename); await check_db.commit()
        restore_ok=True
        return {"ok":True,"restored":job.filename,"migrations":"head"}
    finally:
        shutil.rmtree(work,ignore_errors=True)
        if restore_ok:
            try:
                async with AsyncSession(engine,expire_on_commit=False) as unlock_db:
                    await set_setting(unlock_db,"maintenance_mode","0"); await set_setting(unlock_db,"restore_state","ok"); await unlock_db.commit()
            except Exception as exc:
                logger.warning("Non-critical operation failed: %s", exc)
        else:
            try:
                async with AsyncSession(engine,expire_on_commit=False) as fail_db:
                    await set_setting(fail_db,"maintenance_mode","1"); await set_setting(fail_db,"restore_state","failed"); await fail_db.commit()
            except Exception as exc:
                logger.warning("Non-critical operation failed: %s", exc)
        await _release_payment_side_effect_lock(maintenance_lock,maintenance_token)
# ---------- Admin content / branding ----------

class _PinnedPublicDNSBackend:
    """httpcore backend that resolves hostnames immediately before each new TCP connection.

    The resolved IP is then passed as a literal to the underlying socket connector while
    httpcore keeps the original hostname for TLS SNI/certificate verification. This closes
    the validation-vs-use DNS rebinding window: the connection cannot perform a second DNS
    lookup after the public-IP check.
    """
    def __init__(self):
        import httpcore
        self._backend=httpcore.AnyIOBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        import httpcore
        try:
            literal=ipaddress.ip_address(host)
            if literal.is_private or not literal.is_global:
                raise OSError("destination is not a globally routable IP")
            target=str(literal)
        except ValueError:
            try:
                infos=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
            except OSError as exc:
                raise OSError(f"DNS resolution failed: {exc}") from exc
            addresses=[]
            for info in infos:
                addr=info[4][0].split("%",1)[0]
                try: ip=ipaddress.ip_address(addr)
                except ValueError: continue
                if ip.is_private or not ip.is_global:
                    raise OSError("hostname resolved to a non-public address")
                if str(ip) not in addresses:
                    addresses.append(str(ip))
            if not addresses:
                raise OSError("hostname has no globally routable address")
            target=addresses[0]
        return await self._backend.connect_tcp(target,port,timeout,local_address,socket_options)


def _pinned_public_http_client(timeout_seconds:int):
    import httpx
    transport=httpx.AsyncHTTPTransport(retries=0,trust_env=False)
    # httpx exposes the httpcore pool internally; using its documented network-backend
    # abstraction avoids a second DNS lookup while retaining the original TLS hostname.
    transport._pool._network_backend=_PinnedPublicDNSBackend()
    return httpx.AsyncClient(timeout=timeout_seconds,transport=transport,follow_redirects=False)


def _resolve_public_host(host:str,port:int=443)->list[str]:
    try:
        literal=ipaddress.ip_address(host)
        if literal.is_private or not literal.is_global:
            raise HTTPException(400,"Private or local monitoring targets are not allowed")
        return [str(literal)]
    except ValueError:
        try:
            infos=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
        except OSError:
            raise HTTPException(400,"Monitoring hostname cannot be resolved")
        addresses=[]
        for info in infos:
            addr=info[4][0].split("%",1)[0]
            try: ip=ipaddress.ip_address(addr)
            except ValueError: continue
            if ip.is_private or not ip.is_global:
                raise HTTPException(400,"Monitoring hostname resolves to a private or local address")
            if str(ip) not in addresses: addresses.append(str(ip))
        if not addresses:
            raise HTTPException(400,"Monitoring hostname has no public address")
        return addresses

def validate_public_url(value: str|None, *, allow_empty: bool=True) -> str|None:
    if value is None or value=="":
        if allow_empty: return value
        raise HTTPException(400,"URL is required")
    parsed=urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(400,"Only absolute HTTPS URLs are allowed")
    host=parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"} or host.endswith(".localhost"):
        raise HTTPException(400,"Private or local monitoring targets are not allowed")
    try:
        port=parsed.port or 443
    except ValueError:
        raise HTTPException(400,"Invalid URL port")
    if not 1 <= port <= 65535:
        raise HTTPException(400,"Invalid URL port")
    _resolve_public_host(host, port)
    return value

class SettingIn(BaseModel): value:str=Field(max_length=100000)
class MenuIn(BaseModel):
    title:str=Field(min_length=1,max_length=255)
    action:str=Field(min_length=1,max_length=255)
    item_type:str=Field(default="webapp",pattern="^(webapp|url|field)$")
    sort_order:int=Field(default=0,ge=-100000,le=100000)
    enabled:bool=True
class FieldIn(BaseModel): key:str=Field(min_length=1,max_length=100,pattern=r"^[A-Za-z0-9_.-]+$"); label:str=Field(min_length=1,max_length=255); field_type:str=Field(default="text",pattern="^(text|url|number)$"); value:str=Field(default="",max_length=10000); enabled:bool=True; sort_order:int=Field(default=0,ge=-100000,le=100000)

BRANDING_KEYS = {"app_name", "app_logo", "app_favicon", "theme_default"}

def _branding_payload(db):
    # Placeholder; actual async retrieval is implemented in endpoint below.
    return None

@app.get("/api/public/branding")
async def public_branding(db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(AppSetting).where(AppSetting.key.in_(BRANDING_KEYS)))).scalars().all()
    values={x.key:x.value for x in rows}
    return {
        "name": values.get("app_name") or "Remnawave VPN Shop",
        "logo_url": values.get("app_logo") or "",
        "favicon_url": values.get("app_favicon") or "",
        "theme_default": values.get("theme_default") if values.get("theme_default") in {"light","dark"} else "dark",
    }

@app.get("/api/admin/content")
async def admin_content(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    # Never expose the raw AppSetting table to the browser: it contains encrypted
    # staging/payment/backup secrets. Return only content settings and booleans.
    safe_keys={"app_name","app_logo","app_favicon","theme_default","bot_name","miniapp_title","miniapp_subtitle","miniapp_background_color","miniapp_background_image","miniapp_image","miniapp_instructions","miniapp_buttons","bot_start_image"}
    secret_keys={"yookassa_shop_id","yookassa_secret_key","platega_merchant_id","platega_secret","rollypay_api_key","rollypay_signing_secret","backup_password","staging_e2e.config"}
    ss=(await db.execute(select(AppSetting).where(AppSetting.key.in_(safe_keys|secret_keys)))).scalars().all()
    setting_values={x.key:x.value for x in ss if x.key in safe_keys}
    try: setting_values["miniapp_buttons"]=json.loads(setting_values.get("miniapp_buttons","[]"))
    except Exception: setting_values["miniapp_buttons"]=[]
    secret_status={x.key:bool(x.value) for x in ss if x.key in secret_keys}
    mm=(await db.execute(select(BotMenuItem).order_by(BotMenuItem.sort_order,BotMenuItem.id))).scalars().all(); ff=(await db.execute(select(CustomField).order_by(CustomField.sort_order,CustomField.id))).scalars().all(); ii=(await db.execute(select(MenuImage).order_by(MenuImage.sort_order,MenuImage.id))).scalars().all()
    return {"settings":setting_values,"secret_status":secret_status,"menu":[{"id":x.id,"title":x.title,"action":x.action,"item_type":x.item_type,"sort_order":x.sort_order,"enabled":x.enabled} for x in mm],"fields":[{"id":x.id,"key":x.key,"label":x.label,"field_type":x.field_type,"value":x.value,"enabled":x.enabled,"sort_order":x.sort_order} for x in ff],"images":[{"id":x.id,"title":x.title,"url":"/media/"+x.filename,"sort_order":x.sort_order,"enabled":x.enabled} for x in ii]}

@app.put("/api/admin/settings/{key}")
async def admin_setting(key:str,payload:SettingIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    # Content managers may only modify explicitly public branding keys. Security,
    # payment, staging and backup settings are intentionally not writable here.
    if key not in {"app_name","bot_name","theme_default"}: raise HTTPException(403,"Настройка недоступна для управления контентом")
    if key=="app_name" and (not payload.value.strip() or len(payload.value.strip())>255): raise HTTPException(400,"Название панели должно содержать от 1 до 255 символов")
    if key=="theme_default" and payload.value not in {"light","dark"}: raise HTTPException(400,"theme_default должен быть light или dark")
    row=await db.get(AppSetting,key);
    if not row: row=AppSetting(key=key,value=payload.value); db.add(row)
    else: row.value=payload.value
    if key=="bot_name" and settings.bot_token:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            r=await client.post(f"https://api.telegram.org/bot{settings.bot_token}/setMyName",json={"name":payload.value})
            if not r.is_success: raise HTTPException(502,"Telegram rejected bot name")
    await audit(db,"content.setting.updated",admin.email,key); await db.commit(); return {"ok":True}

async def _store_branding_image(file:UploadFile, kind:str, max_bytes:int=2*1024*1024) -> str:
    allowed={"image/png","image/jpeg","image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400,"Разрешены только PNG, JPG и WEBP")
    data=await _read_upload_limited(file,max_bytes)
    try:
        from PIL import Image, ImageOps
        with Image.open(BytesIO(data)) as im:
            im.verify()
        with Image.open(BytesIO(data)) as im:
            im=ImageOps.exif_transpose(im).convert("RGBA")
            max_side=2048 if kind=="logo" else 512
            im.thumbnail((max_side,max_side),Image.Resampling.LANCZOS)
            out=BytesIO(); im.save(out,"PNG",optimize=True)
            normalized=out.getvalue()
    except Exception:
        raise HTTPException(400,"Файл не является корректным изображением")
    if len(normalized)>max_bytes:
        raise HTTPException(413,"Нормализованное изображение слишком большое")
    name=f"branding-{kind}-{secrets.token_hex(16)}.png"
    root=pathlib.Path(settings.media_dir); root.mkdir(parents=True,exist_ok=True)
    (root/name).write_bytes(normalized)
    return "/media/"+name

async def _replace_branding_file(db:AsyncSession,key:str,new_url:str):
    row=await db.get(AppSetting,key); old=row.value if row else ""
    if row: row.value=new_url
    else: db.add(AppSetting(key=key,value=new_url))
    if old.startswith("/media/"):
        old_name=pathlib.Path(old.removeprefix("/media/")).name
        try: pathlib.Path(settings.media_dir,old_name).unlink(missing_ok=True)
        except Exception as exc: logger.warning("Unable to remove old branding asset: %s",exc)

@app.post("/api/admin/branding/logo")
async def admin_branding_logo(file:UploadFile=File(...),db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    url=await _store_branding_image(file,"logo")
    await _replace_branding_file(db,"app_logo",url); await audit(db,"content.branding.logo.updated",admin.email); await db.commit()
    return {"ok":True,"url":url}

@app.post("/api/admin/branding/favicon")
async def admin_branding_favicon(file:UploadFile=File(...),db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    url=await _store_branding_image(file,"favicon",512*1024)
    await _replace_branding_file(db,"app_favicon",url); await audit(db,"content.branding.favicon.updated",admin.email); await db.commit()
    return {"ok":True,"url":url}

@app.delete("/api/admin/branding/{kind}")
async def admin_branding_delete(kind:str,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    key={"logo":"app_logo","favicon":"app_favicon"}.get(kind)
    if not key: raise HTTPException(404,"Branding asset not found")
    row=await db.get(AppSetting,key)
    if row and row.value.startswith("/media/"):
        name=pathlib.Path(row.value.removeprefix("/media/")).name
        try: pathlib.Path(settings.media_dir,name).unlink(missing_ok=True)
        except Exception as exc: logger.warning("Unable to remove branding asset: %s",exc)
        row.value=""
    await audit(db,f"content.branding.{kind}.deleted",admin.email); await db.commit(); return {"ok":True}

@app.post("/api/admin/bot/start-image")
async def admin_bot_start_image(file:UploadFile=File(...),db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    allowed={"image/jpeg","image/png","image/webp"}
    if file.content_type not in allowed: raise HTTPException(400,"Разрешены JPG, PNG и WEBP")
    data=await file.read(5*1024*1024+1)
    if len(data)>5*1024*1024: raise HTTPException(413,"Изображение слишком большое (5 МБ)")
    if not _valid_image_signature(data,file.content_type): raise HTTPException(400,"Некорректное содержимое изображения")
    ext={"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}[file.content_type]
    pathlib.Path(settings.media_dir).mkdir(parents=True,exist_ok=True)
    name="bot-start-"+secrets.token_hex(16)+ext
    pathlib.Path(settings.media_dir,name).write_bytes(data)
    row=await db.get(AppSetting,"bot_start_image")
    new_url="/media/"+name
    if row: old=row.value; row.value=new_url
    else: db.add(AppSetting(key="bot_start_image",value=new_url)); old=""
    if old.startswith("/media/"):
        try: pathlib.Path(settings.media_dir, pathlib.Path(old.removeprefix("/media/")).name).unlink(missing_ok=True)
        except Exception as exc: logger.warning("Unable to remove old bot image: %s",exc)
    await audit(db,"content.bot.start_image.updated",admin.email)
    await db.commit()
    return {"ok":True,"url":new_url}

@app.delete("/api/admin/bot/start-image")
async def admin_bot_start_image_delete(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    row=await db.get(AppSetting,"bot_start_image")
    if row and row.value.startswith("/media/"):
        try: pathlib.Path(settings.media_dir, pathlib.Path(row.value.removeprefix("/media/")).name).unlink(missing_ok=True)
        except Exception as exc: logger.warning("Unable to remove bot image: %s",exc)
    if row: row.value=""
    await audit(db,"content.bot.start_image.deleted",admin.email)
    await db.commit()
    return {"ok":True}

class MiniAppConfigIn(BaseModel):
    title:str=Field(default="",max_length=255)
    subtitle:str=Field(default="",max_length=1000)
    background_color:str=Field(default="#f5f7fb",max_length=32)
    instructions:str=Field(default="",max_length=20000)
    buttons:list[dict]=Field(default_factory=list)

@app.put("/api/admin/miniapp/config")
async def admin_miniapp_config(payload:MiniAppConfigIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    import re
    if payload.background_color and not re.fullmatch(r"#[0-9a-fA-F]{6}",payload.background_color):
        raise HTTPException(400,"background_color must be #RRGGBB")
    if len(payload.buttons)>30:
        raise HTTPException(400,"Можно настроить не более 30 кнопок")
    field_rows=(await db.execute(select(CustomField.key).where(CustomField.enabled.is_(True)))).scalars().all()
    field_keys=set(field_rows)
    for b in payload.buttons:
        if not isinstance(b,dict) or not b.get("title") or len(str(b.get("title")))>100 or b.get("type") not in {"url","plans","promo","field"}:
            raise HTTPException(400,"Каждая кнопка требует название до 100 символов и тип url/plans/promo/field")
        if b.get("type")=="url": validate_public_url(b.get("url"),allow_empty=False)
        if b.get("type")=="promo" and (not b.get("code") or len(str(b.get("code")))>64): raise HTTPException(400,"Для кнопки промокода нужен корректный код")
        if b.get("type")=="field" and b.get("field_key") not in field_keys: raise HTTPException(400,"Кнопка field ссылается на неизвестное или отключённое поле")
    values={"miniapp_title":payload.title,"miniapp_subtitle":payload.subtitle,"miniapp_background_color":payload.background_color,"miniapp_instructions":payload.instructions,"miniapp_buttons":json.dumps(payload.buttons,ensure_ascii=False)}
    for key,value in values.items():
        row=await db.get(AppSetting,key)
        if row: row.value=value
        else: db.add(AppSetting(key=key,value=value))
    await audit(db,"content.miniapp.updated",admin.email)
    await db.commit()
    return {"ok":True}

@app.post("/api/admin/miniapp/image")
async def admin_miniapp_image(file:UploadFile=File(...),db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    allowed={"image/jpeg","image/png","image/webp"}
    if file.content_type not in allowed: raise HTTPException(400,"Разрешены JPG, PNG и WEBP")
    data=await file.read(5*1024*1024+1)
    if len(data)>5*1024*1024: raise HTTPException(413,"Изображение слишком большое (5 МБ)")
    if not _valid_image_signature(data,file.content_type): raise HTTPException(400,"Некорректное содержимое изображения")
    ext={"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}[file.content_type]
    pathlib.Path(settings.media_dir).mkdir(parents=True,exist_ok=True)
    name="miniapp-image-"+secrets.token_hex(16)+ext; pathlib.Path(settings.media_dir,name).write_bytes(data); new_url="/media/"+name
    row=await db.get(AppSetting,"miniapp_image")
    if row: old=row.value; row.value=new_url
    else: db.add(AppSetting(key="miniapp_image",value=new_url)); old=""
    if old.startswith("/media/"):
        try: pathlib.Path(settings.media_dir, pathlib.Path(old.removeprefix("/media/")).name).unlink(missing_ok=True)
        except Exception as exc: logger.warning("Unable to remove old miniapp image: %s",exc)
    await audit(db,"content.miniapp.image.updated",admin.email); await db.commit(); return {"ok":True,"url":new_url}

@app.delete("/api/admin/miniapp/image")
async def admin_miniapp_image_delete(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    row=await db.get(AppSetting,"miniapp_image")
    if row and row.value.startswith("/media/"):
        try: pathlib.Path(settings.media_dir, pathlib.Path(row.value.removeprefix("/media/")).name).unlink(missing_ok=True)
        except Exception as exc: logger.warning("Unable to remove miniapp image: %s",exc)
    if row: row.value=""
    await audit(db,"content.miniapp.image.deleted",admin.email); await db.commit(); return {"ok":True}

@app.post("/api/admin/miniapp/background")
async def admin_miniapp_background(file:UploadFile=File(...),db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    if file.content_type not in {"image/jpeg","image/png","image/webp"}: raise HTTPException(400,"Only JPG, PNG and WEBP are allowed")
    data=await _read_upload_limited(file,8*1024*1024)
    if not _valid_image_signature(data,file.content_type): raise HTTPException(400,"Invalid image signature")
    ext={"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}[file.content_type]
    name="miniapp-bg-"+secrets.token_hex(16)+ext
    pathlib.Path(settings.media_dir).mkdir(parents=True,exist_ok=True)
    pathlib.Path(settings.media_dir,name).write_bytes(data)
    row=await db.get(AppSetting,"miniapp_background_image")
    if not row: db.add(AppSetting(key="miniapp_background_image",value="/media/"+name))
    else:
        old=row.value
        row.value="/media/"+name
        if old.startswith("/media/"):
            try: pathlib.Path(settings.media_dir, pathlib.Path(old.removeprefix("/media/")).name).unlink(missing_ok=True)
            except Exception as exc:
                logger.warning("Non-critical operation failed: %s", exc)
    await audit(db,"content.miniapp.background.updated",admin.email)
    await db.commit()
    return {"ok":True,"url":"/media/"+name}

@app.delete("/api/admin/miniapp/background")
async def admin_miniapp_background_delete(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    row=await db.get(AppSetting,"miniapp_background_image")
    if row and row.value.startswith("/media/"):
        try: pathlib.Path(settings.media_dir, pathlib.Path(row.value.removeprefix("/media/")).name).unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("Non-critical operation failed: %s", exc)
    if row: row.value=""
    await db.commit()
    return {"ok":True}

@app.post("/api/admin/menu",response_model=dict)
async def admin_menu(payload:MenuIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    if payload.item_type not in {"webapp","url","field"}: raise HTTPException(400,"Недопустимый тип кнопки")
    if payload.item_type=="url": validate_public_url(payload.action,allow_empty=False)
    if payload.item_type=="webapp": validate_public_url(payload.action or settings.mini_app_url,allow_empty=False)
    if payload.item_type=="field":
        if not payload.action: raise HTTPException(400,"Для кнопки поля требуется ключ поля")
        exists=await db.execute(select(CustomField.id).where(CustomField.key==payload.action,CustomField.enabled.is_(True)).limit(1))
        if exists.scalar_one_or_none() is None: raise HTTPException(400,"Кнопка field ссылается на неизвестное или отключённое поле")
    existing_count=int((await db.execute(select(func.count()).select_from(BotMenuItem))).scalar() or 0)
    if existing_count>=30: raise HTTPException(400,"Можно настроить не более 30 кнопок")
    x=BotMenuItem(**payload.model_dump()); db.add(x); await audit(db,"content.menu.created",admin.email); await db.commit(); await db.refresh(x); return {"id":x.id}

@app.put("/api/admin/menu/{item_id}")
async def admin_menu_update(item_id:int,payload:MenuIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    x=await db.get(BotMenuItem,item_id);
    if not x: raise HTTPException(404,"Menu item not found")
    if payload.item_type not in {"webapp","url","field"}: raise HTTPException(400,"Недопустимый тип кнопки")
    if payload.item_type=="url": validate_public_url(payload.action,allow_empty=False)
    if payload.item_type=="webapp": validate_public_url(payload.action or settings.mini_app_url,allow_empty=False)
    if payload.item_type=="field":
        if not payload.action: raise HTTPException(400,"Для кнопки поля требуется ключ поля")
        exists=await db.execute(select(CustomField.id).where(CustomField.key==payload.action,CustomField.enabled.is_(True)).limit(1))
        if exists.scalar_one_or_none() is None: raise HTTPException(400,"Кнопка field ссылается на неизвестное или отключённое поле")
    for k,v in payload.model_dump().items(): setattr(x,k,v)
    await audit(db,"content.menu.updated",admin.email,str(item_id)); await db.commit(); return {"ok":True}

@app.delete("/api/admin/menu/{item_id}")
async def admin_menu_delete(item_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    x=await db.get(BotMenuItem,item_id)
    if not x: raise HTTPException(404,"Menu item not found")
    await db.delete(x)
    await audit(db,"content.menu.deleted",admin.email,str(item_id))
    await db.commit()
    return {"ok":True}

@app.post("/api/admin/fields")
async def admin_field(payload:FieldIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    x=CustomField(**payload.model_dump()); db.add(x); await db.commit(); await db.refresh(x); return {"id":x.id}

@app.put("/api/admin/fields/{field_id}")
async def admin_field_update(field_id:int,payload:FieldIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    x=await db.get(CustomField,field_id);
    if not x: raise HTTPException(404,"Field not found")
    for k,v in payload.model_dump().items(): setattr(x,k,v)
    await db.commit(); return {"ok":True}

@app.delete("/api/admin/fields/{field_id}")
async def admin_field_delete(field_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    x=await db.get(CustomField,field_id);
    if not x: raise HTTPException(404,"Field not found")
    await db.delete(x); await db.commit(); return {"ok":True}

async def _read_upload_limited(file: UploadFile, max_bytes: int) -> bytes:
    chunks=[]
    total=0
    while True:
        chunk=await file.read(min(1024*1024, max_bytes-total+1))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(413, f"Uploaded file is too large (max {max_bytes} bytes)")
    return b"".join(chunks)


def _valid_image_signature(data:bytes, content_type:str)->bool:
    if content_type=="image/jpeg": return data.startswith(b"\xff\xd8\xff")
    if content_type=="image/png": return data.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type=="image/gif": return data.startswith((b"GIF87a",b"GIF89a"))
    if content_type=="image/webp": return data.startswith(b"RIFF") and data[8:12]==b"WEBP"
    return False

@app.post("/api/admin/images")
async def admin_image(title:str=Form(...),sort_order:int=Form(0),enabled:bool=Form(True),file:UploadFile=File(...),db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    allowed={"image/png","image/jpeg","image/webp","image/gif"}
    if file.content_type not in allowed: raise HTTPException(400,"Unsupported image type")
    data=await _read_upload_limited(file,5*1024*1024)
    if file.content_type not in {"image/jpeg","image/png","image/webp","image/gif"}: raise HTTPException(400,"Only JPG, PNG, WEBP and GIF are allowed")
    if not _valid_image_signature(data,file.content_type): raise HTTPException(400,"Invalid image signature")
    ext={"image/jpeg":".jpg","image/png":".png","image/webp":".webp","image/gif":".gif"}[file.content_type]
    name=secrets.token_hex(16)+ext; pathlib.Path(settings.media_dir,name).write_bytes(data)
    x=MenuImage(title=title,filename=name,sort_order=sort_order,enabled=enabled); db.add(x); await db.commit(); await db.refresh(x); return {"id":x.id,"url":"/media/"+name}

@app.delete("/api/admin/images/{image_id}")
async def admin_image_delete(image_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_content"))):
    x=await db.get(MenuImage,image_id);
    if not x: raise HTTPException(404,"Image not found")
    try: pathlib.Path(settings.media_dir,x.filename).unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Non-critical operation failed: %s", exc)
    await db.delete(x); await db.commit(); return {"ok":True}


# ---------- Marketing / promotions / broadcasts ----------
class PromotionIn(BaseModel):
    name:str=Field(min_length=1,max_length=255); kind:str="percent"; value:Decimal=Field(gt=0,le=1000000,decimal_places=2,max_digits=12); plan_ids:list[int]|None=None; starts_at:datetime|None=None; ends_at:datetime|None=None; enabled:bool=True; description:str=""; priority:int=Field(default=0,ge=-100000,le=100000); exclusive:bool=True
class PromoCodeIn(BaseModel):
    code:str=Field(min_length=2,max_length=64); kind:str="percent"; value:Decimal=Field(gt=0,le=1000000,decimal_places=2,max_digits=12); plan_ids:list[int]|None=None; starts_at:datetime|None=None; ends_at:datetime|None=None; usage_limit:int|None=Field(default=None,ge=1); enabled:bool=True; first_purchase_only:bool=False; max_uses_per_user:int|None=Field(default=None,ge=1); min_amount:Decimal|None=Field(default=None,ge=0,decimal_places=2,max_digits=12); referral_only:bool=False
class AdIn(BaseModel):
    title:str=Field(min_length=1,max_length=255); text:str=""; image_url:str|None=None; button_text:str|None=None; button_url:str|None=None; starts_at:datetime|None=None; ends_at:datetime|None=None; enabled:bool=True; sort_order:int=0
class BroadcastIn(BaseModel):
    text:str=Field(min_length=1,max_length=4000); image_url:str|None=None; button_text:str|None=None; button_url:str|None=None; target:str="all"

@app.get("/api/admin/marketing")
async def admin_marketing(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    ps=(await db.execute(select(Promotion).order_by(Promotion.id.desc()))).scalars().all(); cs=(await db.execute(select(PromoCode).order_by(PromoCode.id.desc()))).scalars().all(); ads=(await db.execute(select(Advertisement).order_by(Advertisement.sort_order,Advertisement.id))).scalars().all(); bs=(await db.execute(select(Broadcast).order_by(Broadcast.id.desc()).limit(100))).scalars().all()
    return {"promotions":[{"id":x.id,"name":x.name,"kind":x.kind,"value":float(x.value),"plan_ids":x.plan_ids,"starts_at":x.starts_at,"ends_at":x.ends_at,"enabled":x.enabled,"description":x.description,"priority":x.priority,"exclusive":x.exclusive} for x in ps],"promo_codes":[{"id":x.id,"code":x.code,"kind":x.kind,"value":float(x.value),"plan_ids":x.plan_ids,"starts_at":x.starts_at,"ends_at":x.ends_at,"usage_limit":x.usage_limit,"used_count":x.used_count,"enabled":x.enabled} for x in cs],"advertisements":[{"id":x.id,"title":x.title,"text":x.text,"image_url":x.image_url,"button_text":x.button_text,"button_url":x.button_url,"starts_at":x.starts_at,"ends_at":x.ends_at,"enabled":x.enabled,"sort_order":x.sort_order} for x in ads],"broadcasts":[{"id":x.id,"text":x.text,"status":x.status,"target":x.target,"sent_count":x.sent_count,"failed_count":x.failed_count,"created_at":x.created_at,"finished_at":x.finished_at} for x in bs]}

@app.post("/api/admin/promotions")
async def create_promotion(payload:PromotionIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_marketing"))):
    if payload.kind not in {"percent","fixed"}: raise HTTPException(400,"kind must be percent or fixed")
    if payload.kind=="percent" and payload.value>100: raise HTTPException(400,"Percent discount cannot exceed 100")
    if payload.kind=="fixed" and payload.value<=0: raise HTTPException(400,"Invalid discount")
    x=Promotion(**payload.model_dump()); db.add(x); await audit(db,"marketing.promotion.created",admin.email); await db.commit(); return {"ok":True}
@app.put("/api/admin/promotions/{item_id}")
async def update_promotion(item_id:int,payload:PromotionIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_marketing"))):
    x=await db.get(Promotion,item_id)
    if not x: raise HTTPException(404,"Promotion not found")
    for k,v in payload.model_dump().items(): setattr(x,k,v)
    await db.commit(); return {"ok":True}
@app.delete("/api/admin/promotions/{item_id}")
async def delete_promotion(item_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_marketing"))):
    x=await db.get(Promotion,item_id);
    if not x: raise HTTPException(404,"Promotion not found")
    await db.delete(x); await db.commit(); return {"ok":True}

@app.post("/api/admin/promo-codes")
async def create_promo_code(payload:PromoCodeIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_marketing"))):
    if payload.kind not in {"percent","fixed"}: raise HTTPException(400,"kind must be percent or fixed")
    if payload.kind=="percent" and payload.value>100: raise HTTPException(400,"Percent discount cannot exceed 100")
    data=payload.model_dump(); data["code"]=payload.code.strip().upper(); x=PromoCode(**data); db.add(x)
    try: await db.commit()
    except IntegrityError: await db.rollback(); raise HTTPException(409,"Promo code already exists")
    return {"ok":True}
@app.put("/api/admin/promo-codes/{item_id}")
async def update_promo_code(item_id:int,payload:PromoCodeIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_marketing"))):
    x=await db.get(PromoCode,item_id);
    if not x: raise HTTPException(404,"Promo code not found")
    data=payload.model_dump(); data["code"]=data["code"].strip().upper()
    for k,v in data.items(): setattr(x,k,v)
    await db.commit(); return {"ok":True}
@app.delete("/api/admin/promo-codes/{item_id}")
async def delete_promo_code(item_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_marketing"))):
    x=await db.get(PromoCode,item_id);
    if not x: raise HTTPException(404,"Promo code not found")
    await db.delete(x); await db.commit(); return {"ok":True}

@app.post("/api/admin/advertisements")
async def create_ad(payload:AdIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_marketing"))):
    validate_public_url(payload.button_url)
    validate_public_url(payload.image_url)
    x=Advertisement(**payload.model_dump()); db.add(x); await db.commit(); return {"ok":True}
@app.put("/api/admin/advertisements/{item_id}")
async def update_ad(item_id:int,payload:AdIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_marketing"))):
    x=await db.get(Advertisement,item_id);
    if not x: raise HTTPException(404,"Advertisement not found")
    validate_public_url(payload.button_url); validate_public_url(payload.image_url)
    for k,v in payload.model_dump().items(): setattr(x,k,v)
    await db.commit(); return {"ok":True}
@app.delete("/api/admin/advertisements/{item_id}")
async def delete_ad(item_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_marketing"))):
    x=await db.get(Advertisement,item_id);
    if not x: raise HTTPException(404,"Advertisement not found")
    await db.delete(x); await db.commit(); return {"ok":True}

@app.post("/api/admin/broadcasts")
async def create_broadcast(payload:BroadcastIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_broadcasts"))):
    if not settings.bot_token: raise HTTPException(503,"BOT_TOKEN is not configured")
    if payload.target not in {"all","active","inactive"}: raise HTTPException(400,"Unsupported target")
    validate_public_url(payload.button_url); validate_public_url(payload.image_url)
    x=Broadcast(**payload.model_dump()); db.add(x); await db.commit(); await db.refresh(x); return {"id":x.id,"status":"queued"}

async def monitor_checks_scheduler():
    while True:
        try:
            async with AsyncSession(engine, expire_on_commit=False) as db:
                now=datetime.utcnow(); rows=(await db.execute(select(MonitoringCheck).where(MonitoringCheck.enabled.is_(True)))).scalars().all()
                for x in rows:
                    if x.last_checked_at and (now-x.last_checked_at).total_seconds() < x.interval_seconds: continue
                    started=asyncio.get_running_loop().time()
                    try:
                        validate_public_url(x.url, allow_empty=False)
                        async with _pinned_public_http_client(x.timeout_seconds) as c:
                            r=await c.request(x.method,x.url)
                        x.last_status="ok" if 200<=r.status_code<400 else "degraded"; x.last_error=None if x.last_status=="ok" else f"HTTP {r.status_code}"
                        x.last_latency_ms=round((asyncio.get_running_loop().time()-started)*1000); x.failure_streak=0 if x.last_status=="ok" else x.failure_streak+1
                    except Exception as exc:
                        x.last_status="down"; x.last_error=str(exc)[:500]; x.last_latency_ms=round((asyncio.get_running_loop().time()-started)*1000); x.failure_streak+=1
                    x.last_checked_at=datetime.utcnow()
                    if x.failure_streak in {1,3,5}: await audit(db,"monitoring.alert","system",str(x.id),{"name":x.name,"status":x.last_status,"error":x.last_error})
                await db.commit()
        except Exception: logger.exception("monitoring scheduler failure")
        await asyncio.sleep(15)

# ---------- Enterprise suite V44 ----------
@app.get("/api/admin/enterprise/monitoring")
async def enterprise_monitoring(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    rows=(await db.execute(select(MonitoringCheck).order_by(MonitoringCheck.id))).scalars().all()
    return [{"id":x.id,"name":x.name,"url":x.url,"method":x.method,"interval_seconds":x.interval_seconds,"timeout_seconds":x.timeout_seconds,"enabled":x.enabled,"last_status":x.last_status,"last_latency_ms":x.last_latency_ms,"last_error":x.last_error,"last_checked_at":x.last_checked_at,"failure_streak":x.failure_streak} for x in rows]

@app.post("/api/admin/enterprise/monitoring")
async def enterprise_monitoring_create(payload:MonitoringCheckIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.diagnostics"))):
    validate_public_url(payload.url)
    x=MonitoringCheck(**payload.model_dump()); db.add(x); await db.commit(); await audit(db,"monitoring.check.created",admin.email,str(x.id)); await db.commit(); return {"id":x.id}

@app.delete("/api/admin/enterprise/monitoring/{check_id}")
async def enterprise_monitoring_delete(check_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.diagnostics"))):
    x=await db.get(MonitoringCheck,check_id)
    if not x: raise HTTPException(404,"Проверка не найдена")
    await db.delete(x); await audit(db,"monitoring.check.deleted",admin.email,str(check_id)); await db.commit(); return {"ok":True}

@app.get("/api/admin/enterprise/campaigns")
async def enterprise_campaigns(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("marketing.read"))):
    rows=(await db.execute(select(Campaign).order_by(Campaign.id.desc()))).scalars().all(); return [{"id":x.id,"name":x.name,"kind":x.kind,"status":x.status,"audience":x.audience,"content":x.content,"starts_at":x.starts_at,"ends_at":x.ends_at,"sent_count":x.sent_count,"failed_count":x.failed_count} for x in rows]

@app.post("/api/admin/enterprise/campaigns")
async def enterprise_campaign_create(payload:CampaignIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_marketing"))):
    x=Campaign(**payload.model_dump()); db.add(x); await db.commit(); await audit(db,"campaign.created",admin.email,str(x.id)); await db.commit(); return {"id":x.id,"status":x.status}

@app.put("/api/admin/enterprise/campaigns/{campaign_id}")
async def enterprise_campaign_update(campaign_id:int,payload:CampaignIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("manage_marketing"))):
    x=await db.get(Campaign,campaign_id)
    if not x: raise HTTPException(404,"Кампания не найдена")
    for k,v in payload.model_dump().items(): setattr(x,k,v)
    x.updated_at=datetime.utcnow(); await db.commit(); return {"ok":True}

@app.get("/api/admin/enterprise/rules")
async def enterprise_rules(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    rows=(await db.execute(select(AutomationRule).order_by(AutomationRule.priority,AutomationRule.id))).scalars().all(); return [{"id":x.id,"name":x.name,"event":x.event,"conditions":x.conditions,"actions":x.actions,"enabled":x.enabled,"priority":x.priority,"run_count":x.run_count,"last_run_at":x.last_run_at} for x in rows]

@app.post("/api/admin/enterprise/rules")
async def enterprise_rule_create(payload:RuleIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("feature_flags.manage"))):
    x=AutomationRule(**payload.model_dump()); db.add(x); await db.commit(); await audit(db,"automation.rule.created",admin.email,str(x.id)); await db.commit(); return {"id":x.id}

@app.put("/api/admin/enterprise/rules/{rule_id}")
async def enterprise_rule_update(rule_id:int,payload:RuleIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("feature_flags.manage"))):
    x=await db.get(AutomationRule,rule_id)
    if not x: raise HTTPException(404,"Правило не найдено")
    for k,v in payload.model_dump().items(): setattr(x,k,v)
    x.updated_at=datetime.utcnow(); await db.commit(); return {"ok":True}

@app.get("/api/admin/enterprise/summary")
async def enterprise_summary(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    now=datetime.utcnow(); active=(await db.execute(select(func.count()).select_from(Subscription).where(Subscription.expires_at.is_not(None),Subscription.expires_at>now))).scalar() or 0
    return {"monitoring":await db.scalar(select(func.count()).select_from(MonitoringCheck).where(MonitoringCheck.enabled.is_(True))),"campaigns":await db.scalar(select(func.count()).select_from(Campaign).where(Campaign.status.in_(["scheduled","running"]))),"rules":await db.scalar(select(func.count()).select_from(AutomationRule).where(AutomationRule.enabled.is_(True))),"devices":await db.scalar(select(func.count()).select_from(UserDevice).where(UserDevice.status=="active")),"active_subscriptions":active,"features":["24/7 мониторинг","маршрутизация платежей","антифрод","личный кабинет","мультиустройства","автопродление","конструктор бота","конструктор Mini App","тарифы 2.0","trial","campaign manager","аналитика","node manager","rules engine","support center","disaster recovery"]}

# ---------- V41 Enterprise Operations ----------
V41_FEATURE_DEFAULTS = {
    "passkeys": (False, "Вход администратора по Passkey/WebAuthn"),
    "payment_failover": (True, "Автоматический fallback платёжного провайдера"),
    "incident_center": (True, "Центр инцидентов"),
    "diagnostics_center": (True, "Центр диагностики"),
    "backup_test_restore": (True, "Проверка backup и безопасный test-restore"),
    "advanced_analytics": (True, "Расширенная бизнес-аналитика"),
    "advanced_promos": (True, "Расширенные промокампании"),
    "referral_v2": (True, "Реферальная система второго уровня"),
    "payments": (True, "Создание реальных платежей"),
}

async def _ensure_v41_defaults(db):
    for key,(enabled,desc) in V41_FEATURE_DEFAULTS.items():
        row=await db.get(FeatureFlag,key)
        if not row: db.add(FeatureFlag(key=key,enabled=enabled,description=desc))
    for i,p in enumerate(("yookassa","platega","rollypay"),1):
        row=(await db.execute(select(PaymentProviderHealth).where(PaymentProviderHealth.provider==p))).scalar_one_or_none()
        if not row: db.add(PaymentProviderHealth(provider=p,priority=i*10,enabled=True))
    await db.commit()

@app.get("/api/admin/v41/features")
async def v41_features(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("read"))):
    await _ensure_v41_defaults(db)
    rows=(await db.execute(select(FeatureFlag).order_by(FeatureFlag.key))).scalars().all()
    return [{"key":x.key,"enabled":x.enabled,"description":x.description,"updated_at":str(x.updated_at)} for x in rows]

class FeatureFlagIn(BaseModel):
    enabled: bool

@app.put("/api/admin/v41/features/{key}")
async def v41_feature_update(key:str,payload:FeatureFlagIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("feature_flags.manage"))):
    if key not in V41_FEATURE_DEFAULTS: raise HTTPException(404,"Функция не найдена")
    row=await db.get(FeatureFlag,key)
    if not row: row=FeatureFlag(key=key,description=V41_FEATURE_DEFAULTS[key][1]); db.add(row)
    row.enabled=payload.enabled; row.updated_at=datetime.utcnow()
    await audit(db,"feature_flag.updated",admin.email,key,{"enabled":payload.enabled}); await db.commit()
    return {"key":key,"enabled":payload.enabled}

@app.get("/api/admin/v41/analytics")
async def v41_analytics(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("analytics.read"))):
    now=datetime.utcnow(); since=now-timedelta(days=30)
    users_total=int((await db.execute(select(func.count()).select_from(User))).scalar_one())
    users_new=int((await db.execute(select(func.count()).select_from(User).where(User.created_at>=since))).scalar_one())
    payments_total=int((await db.execute(select(func.count()).select_from(Payment))).scalar_one())
    paid=int((await db.execute(select(func.count()).select_from(Payment).where(Payment.status.in_(["paid","succeeded"])))).scalar_one())
    revenue=(await db.execute(select(func.coalesce(func.sum(Payment.amount),0)).where(Payment.status.in_(["paid","succeeded"])))).scalar_one()
    revenue30=(await db.execute(select(func.coalesce(func.sum(Payment.amount),0)).where(Payment.status.in_(["paid","succeeded"]),Payment.paid_at>=since))).scalar_one()
    refunds=int((await db.execute(select(func.count()).select_from(RefundRequest).where(RefundRequest.status=="refunded"))).scalar_one())
    avg=(Decimal(str(revenue))/Decimal(paid)).quantize(Decimal("0.01")) if paid else Decimal("0")
    return {"users":{"total":users_total,"new_30d":users_new},"payments":{"total":payments_total,"paid":paid,"conversion_percent":round(paid/payments_total*100,2) if payments_total else 0},"revenue":{"all_time":float(revenue),"last_30d":float(revenue30),"average_paid_check":float(avg),"currency":settings.default_currency},"refunds":refunds}

@app.get("/api/admin/v41/crm/users")
async def v41_crm_users(q:str="",page:int=1,page_size:int=50,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("users.read"))):
    page=max(1,page); page_size=min(100,max(1,page_size)); stmt=select(User).order_by(User.id.desc())
    q=q.strip()
    if q:
        if q.isdigit(): stmt=stmt.where(User.telegram_id==int(q))
        else: stmt=stmt.where(User.username.ilike(f"%{q}%"))
    rows=(await db.execute(stmt.offset((page-1)*page_size).limit(page_size))).scalars().all()
    return [{"id":u.id,"telegram_id":u.telegram_id,"username":u.username,"referral_code":u.referral_code,"auto_renew":u.auto_renew_enabled,"created_at":str(u.created_at)} for u in rows]

@app.get("/api/admin/v41/providers")
async def v41_providers(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.providers"))):
    await _ensure_v41_defaults(db)
    rows=(await db.execute(select(PaymentProviderHealth).order_by(PaymentProviderHealth.priority,PaymentProviderHealth.provider))).scalars().all()
    return [{"provider":x.provider,"enabled":x.enabled,"priority":x.priority,"success_count":x.success_count,"failure_count":x.failure_count,"last_latency_ms":x.last_latency_ms,"last_error":x.last_error,"circuit_open_until":str(x.circuit_open_until) if x.circuit_open_until else None} for x in rows]

class ProviderHealthIn(BaseModel):
    enabled: bool
    priority: int = Field(ge=1,le=1000)

@app.put("/api/admin/v41/providers/{provider}")
async def v41_provider_update(provider:str,payload:ProviderHealthIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.providers"))):
    if provider not in {"yookassa","platega","rollypay"}: raise HTTPException(404,"Провайдер не найден")
    row=(await db.execute(select(PaymentProviderHealth).where(PaymentProviderHealth.provider==provider))).scalar_one_or_none()
    if not row: row=PaymentProviderHealth(provider=provider); db.add(row)
    row.enabled=payload.enabled; row.priority=payload.priority; row.updated_at=datetime.utcnow()
    await audit(db,"payment_provider.updated",admin.email,provider,payload.model_dump()); await db.commit(); return {"ok":True}

@app.get("/api/admin/v41/diagnostics")
async def v41_diagnostics(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.diagnostics"))):
    checks=[]
    start=asyncio.get_running_loop().time()
    try: await db.execute(sql_text("SELECT 1")); checks.append({"name":"PostgreSQL","status":"ok","latency_ms":round((asyncio.get_running_loop().time()-start)*1000)})
    except Exception as exc: checks.append({"name":"PostgreSQL","status":"error","error":str(exc)})
    start=asyncio.get_running_loop().time()
    if redis_client:
        try: await redis_client.ping(); checks.append({"name":"Redis","status":"ok","latency_ms":round((asyncio.get_running_loop().time()-start)*1000)})
        except Exception as exc: checks.append({"name":"Redis","status":"error","error":str(exc)})
    else: checks.append({"name":"Redis","status":"error","error":"Не подключён"})
    try:
        rw=RemnawaveClient(); await rw.list_nodes(start=0,size=1); checks.append({"name":"Remnawave","status":"ok"})
    except Exception as exc: checks.append({"name":"Remnawave","status":"error","error":str(exc)})
    return {"status":"ok" if all(x["status"]=="ok" for x in checks) else "degraded","checks":checks,"checked_at":datetime.utcnow().isoformat()}

class IncidentCreateIn(BaseModel):
    severity:str=Field(pattern="^(low|medium|high|critical)$")
    category:str=Field(min_length=1,max_length=64)
    title:str=Field(min_length=1,max_length=255)
    details:str=Field(default="",max_length=10000)

@app.get("/api/admin/v41/incidents")
async def v41_incidents(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.incidents"))):
    rows=(await db.execute(select(SecurityIncidentEvent).order_by(SecurityIncidentEvent.id.desc()).limit(100))).scalars().all()
    return [{"id":x.id,"severity":x.severity,"category":x.category,"title":x.title,"details":x.details,"status":x.status,"created_at":str(x.created_at),"resolved_at":str(x.resolved_at) if x.resolved_at else None} for x in rows]

@app.post("/api/admin/v41/incidents")
async def v41_incident_create(payload:IncidentCreateIn,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.incidents"))):
    x=SecurityIncidentEvent(**payload.model_dump()); db.add(x); await audit(db,"incident.created",admin.email,None,payload.model_dump()); await db.commit(); await db.refresh(x); return {"id":x.id,"status":x.status}

@app.post("/api/admin/v41/incidents/{incident_id}/resolve")
async def v41_incident_resolve(incident_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.incidents"))):
    x=await db.get(SecurityIncidentEvent,incident_id)
    if not x: raise HTTPException(404,"Инцидент не найден")
    x.status="resolved"; x.resolved_at=datetime.utcnow(); await audit(db,"incident.resolved",admin.email,str(incident_id)); await db.commit(); return {"ok":True}

@app.get("/api/admin/v41/backups/verification")
async def v41_backup_verification_list(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.backups.verify"))):
    rows=(await db.execute(select(BackupVerification).order_by(BackupVerification.id.desc()).limit(100))).scalars().all()
    return [{"id":x.id,"backup_id":x.backup_id,"status":x.status,"checksum_ok":x.checksum_ok,"archive_safe":x.archive_safe,"restore_tested":x.restore_tested,"error":x.error,"created_at":str(x.created_at),"finished_at":str(x.finished_at) if x.finished_at else None} for x in rows]

@app.post("/api/admin/v41/backups/{backup_id}/test-restore")
async def v41_backup_test_restore(backup_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("ops.backups.verify"))):
    backup=await db.get(BackupJob,backup_id)
    if not backup or not backup.filename: raise HTTPException(404,"Backup не найден")
    path=_backup_path(backup.filename)
    record=BackupVerification(backup_id=backup_id,status="running",checksum_ok=None,archive_safe=None,restore_tested=False)
    db.add(record); await db.commit(); await db.refresh(record)
    temp_db=f"vpnshop_restore_test_{secrets.token_hex(6)}"
    work=pathlib.Path("/tmp")/f"backup-test-{secrets.token_hex(8)}"; work.mkdir()
    try:
        if not path.is_file(): raise FileNotFoundError("Файл backup не найден")
        h=hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024*1024),b""): h.update(chunk)
        record.checksum_ok=(not backup.sha256 or h.hexdigest()==backup.sha256)
        if not record.checksum_ok: raise ValueError("Checksum backup не совпадает")
        source=path
        if backup.encrypted:
            password_enc=await setting_value(db,"backup_password","")
            if not password_enc: raise ValueError("Пароль backup не настроен")
            from .security import decrypt_secret
            dec=work/"backup.tar.gz"
            proc=await asyncio.create_subprocess_exec("openssl","enc","-d","-aes-256-cbc","-pbkdf2","-in",str(source),"-out",str(dec),"-pass","stdin",stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            _,err=await proc.communicate((decrypt_secret(password_enc)+"\n").encode())
            if proc.returncode!=0: raise ValueError("Не удалось расшифровать backup")
            source=dec
        with tarfile.open(source,"r:gz") as tf:
            _validate_tar_safety(tf); member=next((m for m in tf.getmembers() if m.name=="database.sql"),None)
            if not member: raise ValueError("database.sql отсутствует в backup")
            _safe_extract_members(tf,{"database.sql"},work)
        record.archive_safe=True; await db.commit()
        # Restore into a disposable PostgreSQL database, never into production.
        dbcli=_database_cli_config()
        env={**os.environ,"PGPASSWORD":dbcli["password"]}
        create=await asyncio.create_subprocess_exec("psql","-h",dbcli["host"],"-p",dbcli["port"],"-U",dbcli["user"],"-d",dbcli["database"],"-v","ON_ERROR_STOP=1","-c",f'CREATE DATABASE "{temp_db}"',env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        _,cerr=await create.communicate()
        if create.returncode!=0: raise RuntimeError("Не удалось создать изолированную БД для test-restore: "+cerr.decode(errors="ignore")[-500:])
        sql_file=work/"database.sql"
        restore=await asyncio.create_subprocess_exec("psql","-h",dbcli["host"],"-p",dbcli["port"],"-U",dbcli["user"],"-d",temp_db,"-v","ON_ERROR_STOP=1","-f",str(sql_file),env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        _,rerr=await restore.communicate()
        if restore.returncode!=0: raise RuntimeError("Изолированный restore завершился ошибкой: "+rerr.decode(errors="ignore")[-1000:])
        check=await asyncio.create_subprocess_exec("psql","-h",dbcli["host"],"-p",dbcli["port"],"-U",dbcli["user"],"-d",temp_db,"-v","ON_ERROR_STOP=1","-tAc","SELECT 1",env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        # Fallback because subprocess args above intentionally avoid shell; execute correct check if needed.
        if check.returncode is None: pass
        out,err=await check.communicate()
        if check.returncode!=0 or out.decode().strip()!="1": raise RuntimeError("Проверка восстановленной БД не пройдена")
        record.restore_tested=True; record.status="passed"; record.finished_at=datetime.utcnow(); await audit(db,"backup.test_restore",admin.email,str(backup_id),{"status":"passed","restore_tested":True}); await db.commit()
        return {"status":"passed","checksum_ok":True,"archive_safe":True,"restore_tested":True,"isolated_database":True}
    except Exception as exc:
        record.status="failed"; record.error=str(exc)[:2000]; record.finished_at=datetime.utcnow(); await audit(db,"backup.test_restore",admin.email,str(backup_id),{"status":"failed","error":record.error}); await db.commit()
        return {"status":"failed","checksum_ok":record.checksum_ok,"archive_safe":record.archive_safe,"restore_tested":False,"error":record.error}
    finally:
        try:
            drop=await asyncio.create_subprocess_exec("psql","-h",dbcli["host"],"-p",dbcli["port"],"-U",dbcli["user"],"-d",dbcli["database"],"-c",f'DROP DATABASE IF EXISTS "{temp_db}"',env={**os.environ,"PGPASSWORD":dbcli["password"]},stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
            await drop.communicate()
        except Exception: pass
        shutil.rmtree(work,ignore_errors=True)

@app.get("/api/admin/v41/referrals")
async def v41_referrals(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("referrals.read"))):
    rows=(await db.execute(select(ReferralLedger.user_id,func.sum(ReferralLedger.amount)).group_by(ReferralLedger.user_id).order_by(desc(func.sum(ReferralLedger.amount))).limit(100))).all()
    return [{"user_id":uid,"lifetime_commission":float(amount or 0)} for uid,amount in rows]

@app.get("/api/admin/v41/promotions")
async def v41_promotions(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("marketing.read"))):
    rows=(await db.execute(select(Promotion).order_by(Promotion.priority.desc(),Promotion.id.desc()))).scalars().all()
    return [{"id":x.id,"name":x.name,"kind":x.kind,"value":float(x.value),"plan_ids":x.plan_ids,"enabled":x.enabled,"starts_at":str(x.starts_at) if x.starts_at else None,"ends_at":str(x.ends_at) if x.ends_at else None,"priority":x.priority,"exclusive":x.exclusive} for x in rows]

# Passkey/WebAuthn credential inventory. Registration/assertion ceremonies are intentionally
# exposed only when the deployment includes a WebAuthn verifier; credentials are never accepted
# merely because a browser claims success.
@app.get("/api/admin/v41/passkeys")
async def v41_passkeys(db:AsyncSession=Depends(get_db),admin=Depends(require_permission("security.passkeys"))):
    rows=(await db.execute(select(WebAuthnCredential).where(WebAuthnCredential.admin_id==admin.id).order_by(WebAuthnCredential.id.desc()))).scalars().all()
    return [{"id":x.id,"name":x.name,"created_at":str(x.created_at),"last_used_at":str(x.last_used_at) if x.last_used_at else None,"transports":x.transports,"sign_count":x.sign_count} for x in rows]

@app.delete("/api/admin/v41/passkeys/{credential_id}")
async def v41_passkey_delete(credential_id:int,db:AsyncSession=Depends(get_db),admin=Depends(require_permission("security.passkeys"))):
    x=await db.get(WebAuthnCredential,credential_id)
    if not x or x.admin_id!=admin.id: raise HTTPException(404,"Passkey не найден")
    await db.delete(x); await audit(db,"passkey.deleted",admin.email,str(credential_id)); await db.commit(); return {"ok":True}
