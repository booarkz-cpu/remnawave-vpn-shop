"""Read the latest GitHub release for this repository.

The API reports whether a newer tag exists. The host script
`scripts/update-from-github.sh` downloads that release, checks SHA-256
and applies it. The API process does not extract archives.
"""
from __future__ import annotations

from fastapi import HTTPException

GITHUB_REPO = "booarkz-cpu/remnawave-vpn-shop"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
DOWNLOAD_PREFIX = f"https://github.com/{GITHUB_REPO}/releases/download/"


def version_tuple(value: str) -> tuple:
    numbers = []
    for piece in value.lstrip("v").split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        numbers.append(int(digits or 0))
    return tuple(numbers)


def release_status(current: str, payload: dict) -> dict:
    tag = str(payload.get("tag_name") or "")
    assets = []
    for item in payload.get("assets") or []:
        url = str(item.get("browser_download_url") or "")
        name = str(item.get("name") or "")
        if not url.startswith(DOWNLOAD_PREFIX) or not name:
            continue
        assets.append({"name": name, "url": url})
    latest = tag.lstrip("v")
    return {
        "repository": GITHUB_REPO,
        "current": current,
        "latest": latest,
        "tag": tag,
        "update_available": bool(latest) and version_tuple(latest) > version_tuple(current),
        "assets": assets,
        "apply_command": "sudo bash /opt/vpn-shop/scripts/update-from-github.sh",
    }


async def fetch_latest_release() -> dict:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False, trust_env=False) as client:
            response = await client.get(
                GITHUB_API,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "RemnawaveShop-Updater"},
            )
    except Exception:
        raise HTTPException(502, "GitHub не ответил")
    if response.status_code != 200:
        raise HTTPException(502, "GitHub не ответил")
    data = response.json()
    if not isinstance(data, dict) or not data.get("tag_name"):
        raise HTTPException(502, "GitHub не ответил")
    return data
