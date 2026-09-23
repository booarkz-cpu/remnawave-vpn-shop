import logging
import asyncio
import httpx
from datetime import datetime
from .config import settings

logger = logging.getLogger("remnawave.remnawave")

_SECRET_MARKERS = (
    "password",
    "token",
    "secret",
    "subscription",
    "trojan",
    "vless",
    "shortuuid",
    "suburl",
    "connectionkey",
    "rawkey",
    "sspassword",
)


def redact_remote(value):
    """Drop VPN credentials from a Remnawave payload before it reaches a read-only admin response."""
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("_", "")
            if any(marker in normalized for marker in _SECRET_MARKERS):
                continue
            clean[key] = redact_remote(item)
        return clean
    if isinstance(value, list):
        return [redact_remote(item) for item in value]
    return value

class RemnawaveError(RuntimeError):
    pass

class RemnawaveCircuitOpen(RemnawaveError):
    pass

class RemnawaveClient:
    _shared_client: httpx.AsyncClient | None = None
    _client_lock: asyncio.Lock | None = None

    def __init__(self):
        self.base=settings.remnawave_url.rstrip("/")
        self.headers={
            "Authorization":f"Bearer {settings.remnawave_token}",
            "Accept":"application/json",
            "Content-Type":"application/json",
        }

    @classmethod
    async def _get_shared_client(cls) -> httpx.AsyncClient:
        if cls._shared_client is not None and not cls._shared_client.is_closed:
            return cls._shared_client
        if cls._client_lock is None:
            cls._client_lock = asyncio.Lock()
        async with cls._client_lock:
            if cls._shared_client is None or cls._shared_client.is_closed:
                cls._shared_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(15.0, connect=5.0),
                    limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
                    trust_env=False,
                )
            return cls._shared_client

    @classmethod
    async def close_shared_client(cls):
        if cls._shared_client is not None and not cls._shared_client.is_closed:
            await cls._shared_client.aclose()
        cls._shared_client = None

    async def _request(self,method,path,**kwargs):
        # Redis-backed circuit breaker prevents retry storms when Remnawave is unavailable.
        from .main import redis_client
        fail_key="rw:cb:fail"; open_key="rw:cb:open"
        if redis_client is not None:
            try:
                if await redis_client.get(open_key): raise RemnawaveCircuitOpen("Remnawave circuit breaker is open")
            except RemnawaveCircuitOpen: raise
            except Exception as exc:
                logger.warning("Non-critical operation failed: %s", exc)
        try:
            c=await self._get_shared_client()
            r=await c.request(method,f"{self.base}{path}",headers=self.headers,**kwargs)
            if r.is_error:
                raise RemnawaveError(f"{method} {path}: {r.status_code}: {r.text[:1000]}")
            if redis_client is not None:
                try: await redis_client.delete(fail_key)
                except Exception as exc:
                    logger.warning("Redis circuit-breaker reset failed: %s", exc)
            return r.json() if r.content else {}
        except Exception:
            if redis_client is not None:
                try:
                    n=int(await redis_client.incr(fail_key)); await redis_client.expire(fail_key,300)
                    if n >= settings.remnawave_cb_failures:
                        await redis_client.set(open_key,"1",ex=settings.remnawave_cb_cooldown)
                except Exception as exc:
                    logger.warning("Non-critical operation failed: %s", exc)
            raise

    async def get_user(self,user_id:int|str):
        return await self._request("GET",f"/api/users/{user_id}")

    async def get_user_by_username(self,username:str):
        return await self._request("GET",f"/api/users/by-username/{username}")

    async def stream_users(self,telegram_id=None,cursor=None,size=250,status=None):
        params={"size":min(max(size,1),1000)}
        if telegram_id is not None: params["telegramId"]=telegram_id
        if cursor is not None: params["cursor"]=cursor
        if status: params["status"]=status
        return await self._request("GET","/api/users/stream",params=params)

    async def list_users(self,start=0,size=25):
        return await self._request("GET","/api/users",
                                   params={"start":start,"size":min(size,1000)})

    async def create_user(self,username,expire_at,traffic_limit_bytes=0,
                          traffic_limit_strategy="NO_RESET",
                          active_internal_squads=None,telegram_id=None):
        payload={
            "username":username,
            "expireAt":expire_at.isoformat(),
            "trafficLimitBytes":traffic_limit_bytes,
            "trafficLimitStrategy":traffic_limit_strategy,
        }
        if active_internal_squads is not None:
            payload["activeInternalSquads"]=active_internal_squads
        if telegram_id is not None:
            payload["telegramId"]=telegram_id
        return await self._request("POST","/api/users",json=payload)


    async def get_expiry(self,user_id:int|str):
        data=await self.get_user(user_id)
        value=data.get("expireAt") or data.get("expire_at") or data.get("expiresAt") or data.get("expires_at")
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z","+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    async def extend_idempotent(self,user_id:int|str,days:int,expected_before:datetime,expected_after:datetime):
        current=await self.get_expiry(user_id)
        if current and current >= expected_after:
            return {"already_applied":True,"user":None,"expires_at":current}
        # Never blindly extend when the remote expiry has advanced beyond the
        # operation's original starting point. That means another operation may have
        # won the race (or an earlier request may have succeeded before its response
        # was lost). Extending again would turn an uncertain retry into a double grant.
        if current and current > expected_before:
            raise RemnawaveError("Remote expiry advanced unexpectedly; reconciliation is required")
        await self.extend_user(user_id,days)
        verified=await self.get_expiry(user_id)
        if not verified or verified < expected_after:
            raise RemnawaveError("Remote extension could not be verified")
        return {"already_applied":False,"user":None,"expires_at":verified}

    async def patch_user(self,user_id:int|str,payload:dict):
        body=dict(payload); body["id"]=user_id
        return await self._request("PATCH","/api/users",json=body)

    async def extend_user(self,user_id:int|str,days:int):
        return await self._request("POST",f"/api/users/{user_id}/actions/extend",
                                   json={"days":days})

    async def update_entitlements(self,user_id:int|str,traffic_limit_gb:int|None,profile_id:str|None):
        # None is an explicit unlimited/empty entitlement, not "leave the old
        # remote value untouched". Otherwise downgrading to an unlimited/no-profile
        # plan would silently retain the previous customer's restrictive quota or
        # privileged internal squad. This must mirror create_user semantics.
        payload={"trafficLimitBytes": int(traffic_limit_gb)*1024**3 if traffic_limit_gb is not None else 0,
                 "activeInternalSquads": [profile_id] if profile_id else []}
        return await self.patch_user(user_id,payload)

    async def disable_user(self,user_id:int|str):
        return await self._request("POST",f"/api/users/{user_id}/actions/disable")

    async def enable_user(self,user_id:int|str):
        return await self._request("POST",f"/api/users/{user_id}/actions/enable")

    async def reset_traffic(self,user_id:int|str):
        return await self._request("POST",f"/api/users/{user_id}/actions/reset-traffic")

    async def get_subscription(self,user_id:int|str):
        return await self._request("GET",f"/api/subscriptions/by-id/{user_id}")

    async def get_connection_keys(self,user_id:int|str):
        return await self._request("GET",f"/api/subscriptions/connection-keys/{user_id}")

    async def accessible_nodes(self,user_id:int|str):
        return await self._request("GET",f"/api/users/{user_id}/accessible-nodes")

    async def list_nodes(self,start=0,size=25):
        return await self._request("GET","/api/nodes",
                                   params={"start":start,"size":min(size,1000)})
