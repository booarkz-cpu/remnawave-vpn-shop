import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _abuse():
    spec = importlib.util.spec_from_file_location("abuse_v260", ROOT / "backend/app/abuse.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_abuse_scoring_collapses_prefixes_and_can_block():
    abuse = _abuse()
    assert abuse.source_prefix("203.0.113.10") == "203.0.113.0/24"
    assert abuse.source_prefix("2001:db8:1:2::5") == "2001:db8:1:2::/64"
    assert abuse.source_prefix("not-an-ip") is None
    now = datetime(2026, 9, 22, 12, 0, 0)
    rows = [
        {
            "ip": f"198.51.{100 + index}.1",
            "seen_at": now,
            "asn": str(index),
            "asn_org": "home",
            "user_agent": f"client-{index}",
            "hwid": f"hw-{index}",
        }
        for index in range(1, 8)
    ]
    thresholds = {
        "analyzers": {name: True for name in abuse.ANALYZERS},
        "max_concurrent_ips": 0,
        "cgnat_buffer": 0,
        "max_travel_km": 50,
        "max_accounts_per_hwid": 2,
    }
    result = abuse.score_observations(rows, device_limit=1, thresholds=thresholds, hwid_accounts=3, torrent=True)
    assert result["score"] == 100
    assert result["recommendation"] == "block"
    assert result["sources"] == 7
    names = {hit["name"] for hit in result["analyzers"]}
    assert {"temporal", "asn", "devices", "hwid", "user_agent", "torrent"} <= names
    detail = next(hit["detail"] for hit in result["analyzers"] if hit["name"] == "temporal")
    assert detail == "7 источников (7 адресов)"


def test_cgnat_buffer_and_hosting_skip():
    abuse = _abuse()
    now = datetime(2026, 9, 22, 12, 0, 0)
    later = now + timedelta(minutes=10)
    mobile = [
        {"ip": f"203.0.113.{index}", "seen_at": now, "mobile": True, "asn_org": "mobile carrier"}
        for index in range(1, 5)
    ]
    quiet = abuse.score_observations(
        mobile,
        device_limit=1,
        thresholds={"analyzers": {"temporal": True}, "cgnat_buffer": 3, "max_concurrent_ips": 0, "max_travel_km": 50},
        hwid_accounts=1,
    )
    assert quiet["score"] == 0
    hosted = [
        {"ip": "203.0.113.1", "seen_at": now, "mobile": True, "asn_org": "Hetzner Online", "lat": 55.75, "lon": 37.62},
        {"ip": "198.51.100.1", "seen_at": later, "mobile": True, "asn_org": "Hetzner Online", "lat": 1.35, "lon": 103.82},
    ]
    far = abuse.score_observations(
        hosted,
        device_limit=1,
        thresholds={"analyzers": {"temporal": True, "geo": True}, "cgnat_buffer": 3, "max_concurrent_ips": 0, "max_travel_km": 50},
        hwid_accounts=1,
    )
    assert any(hit["name"] == "temporal" for hit in far["analyzers"])
    assert any(hit["name"] == "geo" for hit in far["analyzers"])


def test_platform_routes_keep_secrets_and_bounds():
    main = (ROOT / "backend/app/main.py").read_text()
    platform = (ROOT / "backend/app/platform_api.py").read_text()
    models = (ROOT / "backend/app/models.py").read_text()
    migration = (ROOT / "backend/alembic/versions/0038_v2_6_0_platform.py").read_text()
    bot = (ROOT / "backend/app/bot.py").read_text()
    agent = (ROOT / "scripts/node-agent.py").read_text()
    assert 'APP_VERSION = "2.6.0"' in main
    assert "from .platform_api import router as platform_router" in main
    assert "app.include_router(platform_router)" in main
    assert "reject_restricted" in main
    assert "Доступ ограничен" in platform
    assert "Устройство в чёрном списке" in main
    assert '"/api/agent/heartbeat": 120' in main
    assert "prometheus_lines" in main
    summary = platform.split("async def platform_summary", 1)[1].split("@router.put", 1)[0]
    assert "token_hash" not in summary
    assert "secret_hash" not in summary
    assert "secret_encrypted" not in summary
    assert '"auto_hard_block": False' in platform
    assert "message[\"To\"] = admin.email" in platform
    assert "X-Shop-Signature" in platform
    assert '@router.get("/api/v3/status")' in platform
    assert "rw_" in platform
    assert 'revision = "0038_v2_6_0_platform"' in migration
    assert 'down_revision = "0037_v2_5_0_tariff_constructor"' in migration
    assert "class ConnectionObservation" in models
    assert "restricted_at" in models
    assert 'Command("ops")' in bot
    assert "admin_telegram_id" in bot
    assert "shell=True" not in agent
    assert "os.system" not in agent
    assert "AGENT_APPLY_TC" in agent
    assert "X-Agent-Token" in agent
    assert '"throttle", "clear"' in agent


def test_license_and_bilingual_platform_docs():
    license_text = (ROOT / "LICENSE").read_text()
    readme = (ROOT / "README.md").read_text()
    github = (ROOT / "README_GITHUB.md").read_text()
    instruction = (ROOT / "INSTRUCTION.md").read_text()
    security = (ROOT / "SECURITY.md").read_text()
    modules = (ROOT / "MODULES.md").read_text()
    notes = (ROOT / "RELEASE_NOTES_V2_6_0.md").read_text()
    index = (ROOT / "DOCUMENTATION.md").read_text()
    admin = (ROOT / "admin/src/main.tsx").read_text()
    i18n = (ROOT / "admin/src/i18n.tsx").read_text()
    cabinet = (ROOT / "cabinet/index.html").read_text()
    assert "LicenseRef-Proprietary" in license_text
    assert "Проприетарная лицензия" in license_text
    assert "Proprietary License" in license_text
    assert "2.6.0" in readme and "2.5.0" in readme and "2.4.0" in readme
    assert "LICENSE" in readme
    assert "2.6.0" in github
    assert "## 9.5" in instruction
    assert "scripts/node-agent.py" in instruction
    assert "AGENT_APPLY_TC" in instruction
    assert "X-Agent-Token" in security
    assert "API-ключ" in security or "API key" in security
    assert "abuse.py" in modules
    assert "platform_api.py" in modules
    assert "Proprietary" in notes
    assert "2.6.0" in notes
    assert "V44" in index
    assert "Платформа" in admin
    assert '"Платформа": "Platform"' in i18n
    assert "manifest.webmanifest" in cabinet
    assert (ROOT / "deploy/grafana/vpnshop-platform.json").is_file()
    assert (ROOT / "cabinet/public/manifest.webmanifest").is_file()
