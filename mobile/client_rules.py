"""Rules shared by the Android and iOS shop clients. The apps duplicate this logic."""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse

LOCAL_HTTP_HOSTS = frozenset({"localhost", "127.0.0.1", "10.0.2.2"})
NODE_FIELDS = ("name", "country", "status", "users_online")
MOBILE_CLIENTS = frozenset({"android-user", "android-admin", "ios-user", "ios-admin"})
MOBILE_CLIENT_KEY = "b7e1c4a09f6d42e8a1c35b77d0e94f12"
IMPORT_SCHEMES = ("happ", "v2rayng", "streisand")


def normalize_base(raw: str) -> str:
    value = (raw or "").strip().rstrip("/")
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.username or parsed.password or not host or parsed.scheme not in {"https", "http"}:
        raise ValueError("https")
    if parsed.scheme == "http" and host not in LOCAL_HTTP_HOSTS:
        raise ValueError("https")
    if any(ch.isspace() for ch in value):
        raise ValueError("https")
    return value


def public_node(row: dict) -> dict:
    status = str(row.get("status") or "unknown")
    if status not in {"online", "offline", "disabled", "unknown"}:
        status = "unknown"
    name = str(row.get("name") or "node")
    if "://" in name or any(ch.isdigit() for ch in name) and name.count(".") >= 3:
        name = "node"
    return {
        "name": name,
        "country": str(row.get("country") or ""),
        "status": status,
        "users_online": int(row.get("users_online") or 0),
    }


def proof_message(client: str, timestamp: str, method: str, path: str) -> str:
    return f"{client}\n{timestamp}\n{method.upper()}\n{path}"


def client_proof(client: str, timestamp: str, method: str, path: str, key: str = MOBILE_CLIENT_KEY) -> str:
    message = proof_message(client, timestamp, method, path).encode()
    return hmac.new(key.encode(), message, hashlib.sha256).hexdigest()


def subscription_apps(url: str) -> dict:
    if not url.startswith("https://") or any(ch.isspace() for ch in url):
        return {}
    encoded = quote(url, safe="")
    return {
        "happ": f"happ://add/{encoded}",
        "v2rayng": f"v2rayng://install-sub?url={encoded}",
        "streisand": f"streisand://import/{encoded}",
    }


def agent_is_stale(last_seen_at, now=None, minutes: int = 5) -> bool:
    if last_seen_at is None:
        return True
    moment = now or datetime.utcnow()
    if isinstance(last_seen_at, str):
        last_seen_at = datetime.fromisoformat(last_seen_at.replace("Z", ""))
    return moment - last_seen_at > timedelta(minutes=minutes)


def error_detail(payload: str, status: int) -> str:
    try:
        data = json.loads(payload or "{}")
    except json.JSONDecodeError:
        return f"HTTP {status}"
    detail = data.get("detail")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()[:300]
    if isinstance(detail, list) and detail:
        first = detail[0]
        if isinstance(first, dict) and first.get("msg"):
            return str(first["msg"])[:300]
    return f"HTTP {status}"
