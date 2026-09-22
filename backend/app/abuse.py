"""Subscription-sharing score. Original rules, not a port of any third-party panel."""
from __future__ import annotations

import ipaddress
import math
from datetime import datetime
from decimal import Decimal

ANALYZERS = ("temporal", "geo", "asn", "behavior", "devices", "hwid", "user_agent", "torrent")
HOSTING_HINTS = ("datacenter", "hosting", "cloud", "vps", "vpn", "hetzner", "ovh", "digitalocean", "amazon", "google", "azure", "leaseweb")


def source_prefix(ip: str) -> str | None:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None
    bits = 24 if addr.version == 4 else 64
    return str(ipaddress.ip_network(f"{addr}/{bits}", strict=False))


def _hosting(org: str) -> bool:
    text = (org or "").lower()
    return any(hint in text for hint in HOSTING_HINTS)


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def recommendation(score: int) -> str:
    if score < 20:
        return "observe"
    if score < 40:
        return "warn"
    if score < 60:
        return "review"
    if score < 80:
        return "throttle"
    return "block"


def score_observations(rows: list[dict], *, device_limit: int | None, thresholds: dict, hwid_accounts: int = 1, torrent: bool = False) -> dict:
    enabled = thresholds.get("analyzers") or {name: True for name in ANALYZERS}
    max_ips = int(thresholds.get("max_concurrent_ips") or 0)
    limit = max_ips or max(1, int(device_limit or 1))
    buffer = int(thresholds.get("cgnat_buffer") or 0)
    max_km = float(thresholds.get("max_travel_km") or 50)
    hits = []
    prefixes = {}
    points = []
    asns = set()
    uas = set()
    hwids = set()
    hours = set()
    addresses = 0
    for row in rows:
        ip = str(row.get("ip") or "")
        prefix = source_prefix(ip)
        if not prefix:
            continue
        addresses += 1
        org = str(row.get("asn_org") or "")
        mobile = bool(row.get("mobile")) and not _hosting(org)
        prefixes.setdefault(prefix, {"mobile": mobile, "ips": set()})
        prefixes[prefix]["ips"].add(ip)
        prefixes[prefix]["mobile"] = prefixes[prefix]["mobile"] or mobile
        if row.get("asn"):
            asns.add(str(row["asn"]))
        if row.get("user_agent"):
            uas.add(str(row["user_agent"])[:80])
        if row.get("hwid"):
            hwids.add(str(row["hwid"]))
        seen = row.get("seen_at")
        if isinstance(seen, datetime):
            hours.add(seen.hour)
        lat, lon = row.get("lat"), row.get("lon")
        if isinstance(lat, (int, float, Decimal)) and isinstance(lon, (int, float, Decimal)) and isinstance(seen, datetime):
            points.append((float(lat), float(lon), seen))
    sources = len(prefixes)
    extra = buffer if prefixes and all(item["mobile"] for item in prefixes.values()) else 0
    if enabled.get("temporal") and sources > limit + extra:
        hits.append({"name": "temporal", "weight": min(40, (sources - limit - extra) * 15), "detail": f"{sources} источников ({addresses} адресов)"})
    if enabled.get("geo") and len(points) >= 2:
        points.sort(key=lambda item: item[2])
        far = 0.0
        for left, right in zip(points, points[1:]):
            minutes = abs((right[2] - left[2]).total_seconds()) / 60
            distance = _km((left[0], left[1]), (right[0], right[1]))
            if minutes <= 30 and distance > max_km:
                far = max(far, distance)
        if far:
            hits.append({"name": "geo", "weight": 25, "detail": f"{int(far)} км за короткое окно"})
    if enabled.get("asn") and len(asns) > 2:
        hits.append({"name": "asn", "weight": min(20, (len(asns) - 2) * 8), "detail": f"{len(asns)} ASN"})
    if enabled.get("behavior") and len(hours) >= 18 and sources > limit:
        hits.append({"name": "behavior", "weight": 15, "detail": f"{len(hours)} разных часов"})
    if enabled.get("devices") and device_limit and len(hwids) > int(device_limit):
        hits.append({"name": "devices", "weight": 20, "detail": f"{len(hwids)} устройств при лимите {device_limit}"})
    if enabled.get("hwid") and hwid_accounts > int(thresholds.get("max_accounts_per_hwid") or 2):
        hits.append({"name": "hwid", "weight": 30, "detail": f"{hwid_accounts} аккаунтов на одном HWID"})
    if enabled.get("user_agent") and len(uas) > 3:
        hits.append({"name": "user_agent", "weight": 10, "detail": f"{len(uas)} разных клиентов"})
    if enabled.get("torrent") and torrent:
        hits.append({"name": "torrent", "weight": 35, "detail": "агент сообщил признак торрента"})
    score = min(100, sum(item["weight"] for item in hits))
    return {
        "score": score,
        "recommendation": recommendation(score),
        "analyzers": hits,
        "sources": sources,
        "addresses": addresses,
    }
