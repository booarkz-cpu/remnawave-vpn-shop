"""Bearer sessions for the Android and iOS shop apps.

The web cabinet and admin panel keep the JWT in an HttpOnly cookie. Native
apps send X-Shop-Client and receive the token once in the JSON body instead.
"""
from __future__ import annotations

MOBILE_CLIENTS = frozenset({"android-user", "android-admin", "ios-user", "ios-admin"})


def mobile_client_name(request) -> str:
    name = (request.headers.get("x-shop-client") or "").strip().lower()
    return name if name in MOBILE_CLIENTS else ""


def session_body(request, token: str, body: dict) -> dict:
    if not mobile_client_name(request):
        return body
    return {**body, "access_token": token, "token_type": "bearer"}
