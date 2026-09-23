#!/usr/bin/env python3
"""Download the latest GitHub release zip and check its SHA-256.

Refuses redirects off the official repository, zip entries that escape the
destination, and a release that is not newer than the installed version.
"""
from __future__ import annotations

import hashlib
import io
import json
import stat
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = "booarkz-cpu/remnawave-vpn-shop"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD_PREFIX = f"https://github.com/{REPO}/releases/download/"
MAX_ARCHIVE_BYTES = 80 * 1024 * 1024


def version_tuple(value: str) -> tuple:
    numbers = []
    for piece in value.lstrip("v").split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        numbers.append(int(digits or 0))
    return tuple(numbers)


def current_version(app_dir: Path) -> str:
    text = (app_dir / "backend/app/main.py").read_text(encoding="utf-8")
    marker = 'APP_VERSION = "'
    start = text.index(marker) + len(marker)
    return text[start:text.index('"', start)]


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "RemnawaveShop-Updater"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.geturl().split("/", 3)[2] != "api.github.com":
            raise SystemExit("GitHub redirect is not allowed")
        return json.load(response)


def fail(message: str) -> None:
    print(message)
    raise SystemExit(1)


def download(url: str) -> bytes:
    if not url.startswith(DOWNLOAD_PREFIX):
        fail("Release asset URL is not from this repository")
    request = urllib.request.Request(url, headers={"User-Agent": "RemnawaveShop-Updater"})
    with urllib.request.urlopen(request, timeout=120) as response:
        host = response.geturl().split("/", 3)[2]
        if host not in {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}:
            fail("Release download host is not allowed")
        blob = response.read(MAX_ARCHIVE_BYTES + 1)
    if len(blob) > MAX_ARCHIVE_BYTES:
        fail("Release archive is too large")
    return blob


def safe_extract(blob: bytes, destination: Path) -> None:
    if len(blob) > MAX_ARCHIVE_BYTES:
        fail("Release archive is too large")
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        total = 0
        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                fail("Release archive contains a symlink")
            if name.startswith("/") or name.startswith("../") or ".." in Path(name).parts:
                fail("Release archive contains an unsafe path")
            total += info.file_size
            if total > MAX_ARCHIVE_BYTES:
                fail("Release archive is too large")
            if name.endswith("/") or not name.strip("/"):
                continue
            target = (destination / name).resolve()
            root = destination.resolve()
            if target != root and root not in target.parents:
                fail("Release archive contains an unsafe path")
            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            with archive.open(info) as source, target.open("wb") as handle:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_ARCHIVE_BYTES:
                        fail("Release archive is too large")
                    handle.write(chunk)
    if (destination / "backend/app/main.py").is_file():
        return
    children = [path for path in destination.iterdir() if path.name != "__MACOSX"]
    if len(children) == 1 and children[0].is_dir() and (children[0] / "backend/app/main.py").is_file():
        nested = children[0]
        for item in list(nested.iterdir()):
            target = destination / item.name
            if target.exists():
                fail("Release archive layout is unsafe")
            item.rename(target)
        nested.rmdir()


def main() -> None:
    app_dir = Path(sys.argv[1]).resolve()
    stage = Path(sys.argv[2]).resolve()
    installed = current_version(app_dir)
    payload = fetch_json(API)
    tag = str(payload.get("tag_name") or "")
    latest = tag.lstrip("v")
    if version_tuple(latest) <= version_tuple(installed):
        print(f"Установлена актуальная версия {installed}")
        raise SystemExit(0)
    assets = {item.get("name"): item.get("browser_download_url") for item in payload.get("assets") or []}
    zip_name = next((name for name in assets if str(name).endswith(".zip") and "full_release" in str(name)), "")
    sha_candidates = []
    if zip_name:
        sha_candidates = [zip_name + ".sha256", zip_name.removesuffix(".zip") + ".sha256"]
    sha_name = next((name for name in sha_candidates if name in assets), "")
    if not zip_name or not sha_name:
        fail("В релизе нет zip и sha256")
    blob = download(str(assets[zip_name]))
    digest_line = download(str(assets[sha_name])).decode().strip().split()[0].lower()
    actual = hashlib.sha256(blob).hexdigest()
    if actual != digest_line:
        fail("SHA-256 релиза не совпал")
    stage.mkdir(parents=True, exist_ok=True)
    safe_extract(blob, stage)
    print(latest)


if __name__ == "__main__":
    main()
