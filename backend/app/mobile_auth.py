"""Bearer sessions for the Android and iOS shop apps.

The web cabinet and admin panel keep the JWT in an HttpOnly cookie. Native
apps send X-Shop-Client and receive the token once in the JSON body instead.
A mobile client also sends X-Shop-Time and X-Shop-Proof, an HMAC of the
request, so a bare header is not enough to mint a bearer token.
"""
from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import HTTPException

MOBILE_CLIENTS = frozenset({"android-user", "android-admin", "ios-user", "ios-admin"})
PROOF_WINDOW_SECONDS = 300


def mobile_client_name(request) -> str:
    name = (request.headers.get("x-shop-client") or "").strip().lower()
    return name if name in MOBILE_CLIENTS else ""


def proof_message(client: str, timestamp: str, method: str, path: str) -> str:
    return f"{client}\n{timestamp}\n{method.upper()}\n{path}"


def client_proof(key: str, client: str, timestamp: str, method: str, path: str) -> str:
    message = proof_message(client, timestamp, method, path).encode()
    return hmac.new(key.encode(), message, hashlib.sha256).hexdigest()


def require_mobile_proof(request) -> None:
    from .config import settings

    client = mobile_client_name(request)
    if not client or not settings.mobile_require_proof or not settings.mobile_client_key:
        return
    timestamp = (request.headers.get("x-shop-time") or "").strip()
    proof = (request.headers.get("x-shop-proof") or "").strip().lower()
    try:
        stamp = int(timestamp)
    except ValueError:
        raise HTTPException(401, "Подпись клиента не принята")
    if abs(int(time.time()) - stamp) > PROOF_WINDOW_SECONDS:
        raise HTTPException(401, "Подпись клиента не принята")
    path = request.url.path
    expected = client_proof(settings.mobile_client_key, client, timestamp, request.method, path)
    if not hmac.compare_digest(expected, proof):
        raise HTTPException(401, "Подпись клиента не принята")


def session_body(request, token: str, body: dict) -> dict:
    if not mobile_client_name(request):
        return body
    return {**body, "access_token": token, "token_type": "bearer"}
