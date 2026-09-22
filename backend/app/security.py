import logging
import base64, hashlib, hmac, os, secrets, json
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .config import settings

logger = logging.getLogger("remnawave.security")
from .db import get_db
from .models import AdminUser, AdminSession
from .totp import verify as verify_totp_code

bearer = HTTPBearer(auto_error=False)
PERMISSIONS = {
    "viewer": {"read", "manage_own_mfa", "users.read", "payments.read", "marketing.read", "analytics.read", "support.read"},
    "operator": {"read", "manage_plans", "manage_users", "manage_payments", "manage_content", "manage_marketing", "manage_broadcasts", "manage_own_mfa", "users.read", "users.write", "users.keys", "payments.read", "payments.write", "payments.retry", "marketing.read", "analytics.read", "sessions.self", "referrals.read", "support.read", "support.write", "ops.diagnostics", "ops.incidents", "ops.providers", "ops.backups.verify", "ops.releases", "security.passkeys", "feature_flags.manage"},
    "admin": {"read", "manage_plans", "manage_users", "manage_payments", "manage_content", "manage_marketing", "manage_broadcasts", "provision_nodes", "manage_admins", "manage_backups", "staging_e2e.manage", "manage_own_mfa", "users.read", "users.write", "users.keys", "payments.read", "payments.write", "payments.retry", "payments.refund", "marketing.read", "backups.read", "backups.write", "security.manage", "analytics.read", "sessions.manage", "security.stepup", "payments.reconcile", "referrals.read", "referrals.reconcile", "referrals.withdrawals.read", "referrals.withdrawals.approve", "referrals.withdrawals.pay", "security.manage", "support.read", "support.write", "ops.diagnostics", "ops.incidents", "ops.providers", "ops.backups.verify", "ops.releases", "security.passkeys", "feature_flags.manage"},
}


def _key(secret: str|None = None) -> bytes:
    return hashlib.sha256((secret or settings.app_secret).encode()).digest()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    n, r, p = 2**15, 8, 1
    # OpenSSL's default 32 MiB ceiling rejects n=2**15, r=8. The work factor stays the same.
    digest = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=64, maxmem=64 * 1024 * 1024)
    return f"scrypt${n}${r}${p}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, n, r, p, salt_b64, digest_b64 = encoded.split("$", 5)
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected), maxmem=64 * 1024 * 1024)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def encrypt_secret(value: str) -> str:
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_key()).encrypt(nonce, value.encode(), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode()


def decrypt_secret(value: str) -> str:
    raw = base64.urlsafe_b64decode(value.encode())
    for secret in (settings.app_secret, settings.app_secret_previous):
        if not secret: continue
        try: return AESGCM(_key(secret)).decrypt(raw[:12], raw[12:], None).decode()
        except Exception as exc:
            logger.warning("Non-critical operation failed: %s", exc)
    raise ValueError("Unable to decrypt secret")


def issue_token(admin: AdminUser, mfa_verified: bool, ttl_minutes: int = 30, token_type: str = "admin", jti: str|None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(admin.id), "email": admin.email, "role": admin.role,
               "type": token_type, "mfa": mfa_verified, "iat": int(now.timestamp()),
               "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp())}
    if jti: payload["jti"] = jti
    return jwt.encode(payload, settings.app_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        try:
            return jwt.decode(token, settings.app_secret, algorithms=["HS256"])
        except jwt.PyJWTError:
            if settings.app_secret_previous:
                return jwt.decode(token, settings.app_secret_previous, algorithms=["HS256"])
            raise
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired admin token")


async def revoke_all_admin_sessions(db: AsyncSession, admin_id: int):
    await db.execute(__import__("sqlalchemy").update(AdminSession).where(AdminSession.admin_id==admin_id, AdminSession.revoked_at.is_(None)).values(revoked_at=datetime.utcnow()))

async def current_admin(request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer), db: AsyncSession = Depends(get_db)):
    from .mobile_auth import require_mobile_proof
    require_mobile_proof(request)
    token=credentials.credentials if credentials else request.cookies.get("rw_admin")
    if not token:
        raise HTTPException(401, "Admin authentication required")
    claims = decode_token(token)
    if claims.get("type") != "admin":
        raise HTTPException(403, "Invalid admin token")
    try:
        admin_id=int(claims["sub"])
    except (KeyError,TypeError,ValueError):
        raise HTTPException(401,"Invalid admin token")
    admin = await db.get(AdminUser, admin_id)
    if not admin or admin.disabled:
        raise HTTPException(401, "Admin account disabled or missing")
    jti=claims.get("jti")
    if not jti:
        raise HTTPException(401, "Admin session is not registered")
    session=(await db.execute(select(AdminSession).where(AdminSession.jti_hash==hashlib.sha256(jti.encode()).hexdigest(), AdminSession.revoked_at.is_(None)))).scalar_one_or_none()
    now = datetime.utcnow()
    if not session or session.expires_at < now:
        raise HTTPException(401, "Admin session expired or revoked")
    if session.last_seen_at and session.last_seen_at < now - timedelta(minutes=15):
        session.revoked_at = now
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(401, "Admin session expired by inactivity")
    current_ua = (request.headers.get("user-agent") or "")[:512]
    if session.user_agent and current_ua and session.user_agent != current_ua:
        session.revoked_at = now
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(401, "Admin session device changed")
    session.last_seen_at=now
    # Persist activity immediately; endpoint handlers may not commit if they are read-only.
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(503, "Admin session state could not be persisted")
    if admin.mfa_enabled and not claims.get("mfa"):
        raise HTTPException(403, "MFA verification required")
    return admin


def require_permission(permission: str):
    async def dependency(admin: AdminUser = Depends(current_admin)):
        if permission not in PERMISSIONS.get(admin.role, set()):
            raise HTTPException(403, "Insufficient permissions")
        return admin
    return dependency


def verify_totp(admin: AdminUser, code: str) -> bool:
    if not admin.totp_secret_encrypted:
        return False
    try:
        return verify_totp_code(decrypt_secret(admin.totp_secret_encrypted), code, valid_window=1)
    except Exception:
        return False


def generate_recovery_codes(count: int = 10) -> list[str]:
    return [secrets.token_hex(5).upper() for _ in range(count)]


def set_recovery_codes(admin: AdminUser, codes: list[str]):
    admin.recovery_codes_encrypted = encrypt_secret(json.dumps(codes))


def consume_recovery_code(admin: AdminUser, code: str) -> bool:
    if not admin.recovery_codes_encrypted: return False
    try:
        codes=json.loads(decrypt_secret(admin.recovery_codes_encrypted))
    except Exception:
        return False
    normalized=code.strip().upper()
    if normalized not in codes: return False
    codes.remove(normalized)
    admin.recovery_codes_encrypted=encrypt_secret(json.dumps(codes))
    return True
