"""3.0.0-realise production audit contracts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_identity_and_docs():
    main = (ROOT / "backend/app/main.py").read_text()
    notes = (ROOT / "RELEASE_NOTES_V3_0_0.md").read_text()
    readme = (ROOT / "README.md").read_text()
    checklist = (ROOT / "PRODUCTION_CHECKLIST.md").read_text()
    instruction = (ROOT / "INSTRUCTION.md").read_text()
    assert main.index('APP_VERSION = "3.0.0-realise"') < main.index('APP_VERSION = "2.13.0"')
    assert "3.0.0-realise" in notes and "Русский" in notes and "English" in notes
    assert "3.0.0-realise" in readme and "2.13.0" in readme
    assert "личный кабинет" in readme
    assert "Конструктор тарифов" in readme
    assert "## Русский" in checklist and "## English" in checklist
    assert "9.12" in instruction
    assert "0038_v2_6_0_platform" in notes


def test_package_upload_limit_and_auth_order():
    main = (ROOT / "backend/app/main.py").read_text()
    catalog = (ROOT / "backend/app/mobile_catalog.py").read_text()
    assert "PACKAGE_UPLOAD_BYTES = 80 * 1024 * 1024" in main
    assert "MAX_PACKAGE_BYTES = 80 * 1024 * 1024" in catalog
    assert "def _request_body_limit" in main
    block = main[main.index("class SecurityHeadersMiddleware"): main.index("_METRICS")]
    assert "total > MAX_REQUEST_BYTES" in block
    assert "_request_body_limit" in block
    upload = next(line for line in catalog.splitlines() if line.startswith("async def upload_app_file"))
    assert upload.index("manage_content") < upload.index("UploadFile")
    logo = next(line for line in catalog.splitlines() if line.startswith("async def upload_client_logo"))
    assert logo.index("manage_content") < logo.index("UploadFile")


def test_proxy_and_forwarded_for_are_closed():
    main = (ROOT / "backend/app/main.py").read_text()
    remnawave = (ROOT / "backend/app/remnawave.py").read_text()
    sandbox = (ROOT / "scripts/sandbox-e2e.sh").read_text()
    assert "def _peer_is_trusted_proxy" in main
    assert "forwarded and _peer_is_trusted_proxy(peer)" in main
    assert "trust_env=False" in remnawave
    assert main.count("trust_env=False") >= 4
    assert 'return {"ok":False,"error":"Повтор выдачи не выполнен"}' in main
    assert '"error":"unavailable"' in main
    assert "str(exc)[:300]" not in main[main.index("async def health_summary"): main.index("async def admin_gifts")]
    assert "PYTHON=python3" in sandbox


def test_feature_flags_are_loaded_by_key():
    main = (ROOT / "backend/app/main.py").read_text()
    assert "FeatureFlag.key==key" in main
    assert "db.get(FeatureFlag, key)" not in main
    assert "db.get(FeatureFlag,key)" not in main


def test_audit_log_stores_request_id():
    models = (ROOT / "backend/app/models.py").read_text()
    block = models[models.index("class AuditLog"): models.index("class AppSetting")]
    assert "request_id: Mapped[str|None]" in block


def test_audit_serializes_decimal_plan_prices():
    main = (ROOT / "backend/app/main.py").read_text()
    assert "def _json_ready" in main
    assert "json.dumps(details, ensure_ascii=False, default=_json_ready)" in main


def test_scrypt_allows_the_chosen_work_factor():
    security = (ROOT / "backend/app/security.py").read_text()
    assert "maxmem=64 * 1024 * 1024" in security
    assert security.count("maxmem=64 * 1024 * 1024") >= 2


def test_alembic_version_column_fits_long_revision_ids():
    env = (ROOT / "backend/alembic/env.py").read_text()
    assert "version_num VARCHAR(128) NOT NULL PRIMARY KEY" in env
    assert "ALTER COLUMN version_num TYPE VARCHAR(128)" in env
    too_long = []
    for path in (ROOT / "backend/alembic/versions").glob("*.py"):
        text = path.read_text()
        for line in text.splitlines():
            if line.startswith("revision"):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if len(value) > 32:
                    too_long.append(value)
    assert "0025_v44_5_8_entitlement_idempotency" in too_long
    assert "0030_v44_5_16_privacy_and_refund_integrity" in too_long


def test_helpers_accept_caddy_and_package_size(monkeypatch, tmp_path):
    import ipaddress
    import sys

    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    sys.path.insert(0, str(ROOT / "backend"))
    from app.main import PACKAGE_UPLOAD_BYTES, _peer_is_trusted_proxy, _request_body_limit

    assert _peer_is_trusted_proxy("127.0.0.1") is True
    assert _peer_is_trusted_proxy("10.1.2.3") is True
    assert _peer_is_trusted_proxy("203.0.113.9") is False
    assert _peer_is_trusted_proxy("testclient") is False
    assert _request_body_limit("POST", "/api/admin/apps/android-user/file") == PACKAGE_UPLOAD_BYTES
    assert _request_body_limit("POST", "/api/admin/apps/ios-admin/file") == PACKAGE_UPLOAD_BYTES
    assert _request_body_limit("POST", "/api/payments/create") == 12 * 1024 * 1024
    assert _request_body_limit("GET", "/api/admin/apps/android-user/file") == 12 * 1024 * 1024
    assert ipaddress.ip_address("203.0.113.9").is_global is False
