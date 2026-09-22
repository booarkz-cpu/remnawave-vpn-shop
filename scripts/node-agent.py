#!/usr/bin/env python3
"""Pull-based node agent for Remnawave VPN Shop.

Posts a heartbeat and optional connection observations. Applies only the
queued actions throttle and clear, and only when AGENT_APPLY_TC=1.
The token is sent in a header and is not written to stdout.
"""
from __future__ import annotations

import ipaddress
import json
import os
import pathlib
import shutil
import subprocess
import time
import urllib.error
import urllib.request


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _metrics() -> dict:
    cpu = "0"
    try:
        cpu = pathlib.Path("/proc/loadavg").read_text().split()[0]
    except OSError:
        cpu = "0"
    mem = ""
    try:
        info = {}
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            key, _, rest = line.partition(":")
            info[key] = rest.strip().split()[0]
        total = int(info.get("MemTotal") or 0)
        avail = int(info.get("MemAvailable") or 0)
        if total:
            mem = str(round((total - avail) * 100 / total))
    except (OSError, ValueError):
        mem = ""
    disk = ""
    try:
        usage = shutil.disk_usage("/")
        disk = str(round(usage.used * 100 / usage.total))
    except OSError:
        disk = ""
    xray = False
    proc = pathlib.Path("/proc")
    if proc.is_dir():
        for comm in proc.glob("[0-9]*/comm"):
            try:
                if comm.read_text().strip() == "xray":
                    xray = True
                    break
            except OSError:
                continue
    return {"cpu": cpu[:32], "mem": mem[:32], "disk": disk[:32], "xray_ok": xray, "version": "1"}


def _observations() -> list:
    path = _env("OBSERVATIONS_FILE")
    if not path:
        return []
    try:
        data = json.loads(pathlib.Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return data[:200]


def _global_ip(value: str) -> str | None:
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        return None
    if not addr.is_global:
        return None
    return str(addr)


def _iface() -> str | None:
    name = _env("AGENT_IFACE")
    if not name or len(name) > 15:
        return None
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-")
    if any(ch not in allowed for ch in name):
        return None
    return name


def _apply(actions: list) -> None:
    if _env("AGENT_APPLY_TC") != "1":
        return
    iface = _iface()
    if not iface:
        return
    for action in actions:
        kind = str(action.get("kind") or "")
        if kind not in {"throttle", "clear"}:
            continue
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        ips = payload.get("ips") if isinstance(payload.get("ips"), list) else []
        for raw in ips[:5]:
            ip = _global_ip(str(raw))
            if not ip:
                continue
            if kind == "clear":
                argv = ["tc", "filter", "del", "dev", iface, "protocol", "ip", "parent", "ffff:", "prio", "1"]
            else:
                try:
                    kbps = int(payload.get("kbps") or 1024)
                except (TypeError, ValueError):
                    continue
                if kbps < 64 or kbps > 100000:
                    continue
                argv = [
                    "tc", "filter", "replace", "dev", iface, "parent", "ffff:",
                    "protocol", "ip", "prio", "1", "u32",
                    "match", "ip", "dst", ip,
                    "police", "rate", f"{kbps}kbit", "burst", "32k", "drop",
                ]
            subprocess.run(argv, check=False)


def _post(base: str, path: str, token: str, body: dict) -> dict:
    request = urllib.request.Request(
        base.rstrip("/") + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Agent-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read().decode()
    return json.loads(raw) if raw else {}


def main() -> None:
    base = _env("SHOP_API_BASE")
    token = _env("AGENT_TOKEN")
    if not base or not token:
        raise SystemExit("SHOP_API_BASE and AGENT_TOKEN are required")
    interval = 60
    try:
        interval = max(15, int(_env("AGENT_INTERVAL", "60")))
    except ValueError:
        interval = 60
    while True:
        try:
            beat = _post(base, "/api/agent/heartbeat", token, _metrics())
            _apply(beat.get("actions") or [])
            items = _observations()
            if items:
                _post(base, "/api/agent/observations", token, {"items": items})
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            pass
        time.sleep(interval)


if __name__ == "__main__":
    main()
