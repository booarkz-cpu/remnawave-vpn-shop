"""3.1.2 panel leak audit contracts."""
import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]


def test_version_312_is_first():
    main = (ROOT / "backend/app/main.py").read_text()
    assert main.index('APP_VERSION = "3.1.2"') < main.index('APP_VERSION = "3.1.1"')
    assert main.index('APP_VERSION = "3.1.1"') < main.index('APP_VERSION = "3.1.0"')
    assert main.index('APP_VERSION = "3.1.0"') < main.index('APP_VERSION = "3.0.1"')
    build = (ROOT / "scripts/build-release.sh").read_text()
    assert build.index('VERSION="3.1.2"') < build.index('VERSION="3.1.1"')
    assert build.index('VERSION="3.1.1"') < build.index('VERSION="3.1.0"')
    assert build.index('ARTIFACT="remnawave_vpn_shop_v3_1_2_full_release.zip"') < build.index("remnawave_vpn_shop_v3_1_1_full_release.zip")
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    assert installer.index('INSTALLER_VERSION="3.1.2"') < installer.index('INSTALLER_VERSION="3.1.1"')
    assert installer.index('INSTALLER_VERSION="3.1.1"') < installer.index('INSTALLER_VERSION="3.1.0"')
    manifest = (ROOT / "release-manifest.template.json").read_text()
    assert '"version": "3.1.2"' in manifest
    assert '"previous_release": "3.1.1"' in manifest
    assert "remnawave_vpn_shop_v3_1_2_full_release.zip" in manifest


def test_remote_payload_and_audit_are_redacted():
    os.environ.setdefault("MEDIA_DIR", "/tmp/media")
    sys.path.insert(0, str(ROOT / "backend"))
    from app.main import _public_audit_details, _public_refund_reason, _remote_user_id
    from app.remnawave import redact_remote

    clean = redact_remote({
        "username": "buyer",
        "status": "ACTIVE",
        "subscriptionUrl": "https://secret.example/sub",
        "shortUuid": "abc",
        "trojanPassword": "secret",
        "response": {"users": [{"id": "1", "vlessUuid": "u", "ssPassword": "pw"}]},
    })
    assert clean["username"] == "buyer"
    assert clean["status"] == "ACTIVE"
    assert "subscriptionUrl" not in clean
    assert "shortUuid" not in clean
    assert "trojanPassword" not in clean
    assert clean["response"]["users"][0] == {"id": "1"}
    user_id = "550e8400-e29b-41d4-a716-446655440000"
    assert _remote_user_id(user_id) == user_id
    with pytest.raises(HTTPException) as bad:
        _remote_user_id("../etc/passwd")
    assert bad.value.status_code == 400
    assert bad.value.detail == "Некорректный идентификатор пользователя Remnawave"
    hidden = _public_audit_details('{"provider":"yookassa","error":"dsn leaked","nested":{"token":"abc"}}')
    assert "yookassa" in hidden
    assert "dsn leaked" not in hidden
    assert "abc" not in hidden
    assert hidden.count("unavailable") == 2
    assert _public_audit_details("оператор отметил инцидент") == "оператор отметил инцидент"
    assert _public_refund_reason("клиент просил\nRevoke pending: connection refused") == "клиент просил"
    assert _public_refund_reason("обычная причина") == "обычная причина"


def test_admin_routes_hide_credentials_and_stderr():
    main = (ROOT / "backend/app/main.py").read_text()
    subscription = main[main.index('"/api/admin/remnawave/users/{user_id}/subscription"'): main.index('"/api/admin/remnawave/users/{user_id}/keys"')]
    keys = main[main.index('"/api/admin/remnawave/users/{user_id}/keys"'): main.index('"/api/admin/remnawave/health"')]
    assert 'require_permission("users.keys")' in subscription
    assert 'require_permission("users.keys")' in keys
    assert 'require_permission("read")' not in subscription
    overview = main[main.index("async def admin_overview"): main.index('"/api/admin/plans"')]
    assert "func.count()" in overview
    assert '"response":{"total":total}' in overview
    diagnostics = main[main.index("async def v41_diagnostics"): main.index("class IncidentCreateIn")]
    assert 'str(exc)' not in diagnostics
    assert '"error":"unavailable"' in diagnostics
    assert '"error":"unavailable" if x.error else None' in main
    assert '"last_error":"unavailable" if x.last_error else None' in main
    assert 'raise HTTPException(500, "Restore failed")' in main
    assert 'raise HTTPException(500, "Migration after restore failed")' in main
    assert 'raise HTTPException(500, "Backup failed")' in main
    assert "_public_audit_details(x.details)" in main
    assert "_public_refund_reason(x.reason)" in main
    assert "_public_refund_reason(r.reason)" in main
    provisioner = (ROOT / "backend/app/provisioner.py").read_text()
    body = provisioner[provisioner.index("def run_ssh"):]
    assert '"output"' not in body
    assert 'ProvisionError("Remote install failed")' in body
    assert "err[-4000:]" not in body.split("raise ProvisionError", 1)[1][:200]


def test_docs_describe_312_and_keep_311():
    readme = (ROOT / "README.md").read_text()
    security = (ROOT / "SECURITY.md").read_text()
    instruction = (ROOT / "INSTRUCTION.md").read_text()
    notes = (ROOT / "RELEASE_NOTES_V3_1_2.md").read_text()
    docs = (ROOT / "DOCUMENTATION.md").read_text()
    steps = (ROOT / "INSTALL_STEPS.md").read_text()
    ui = (ROOT / "admin/src/main.tsx").read_text()
    assert "3.1.2" in readme and "3.1.1" in readme and "3.1.0" in readme
    assert "личный кабинет" in readme and "Конструктор тарифов" in readme
    assert "9.16" in readme and "FULL_E2E_PASS" in readme
    assert "3.1.2" in security and "3.1.1" in security and "[скрыто]" in security and "FULL_E2E_PASS" in security
    assert instruction.count("## 9.16.") == 2
    assert instruction.count("## 9.15.") == 2
    assert "FULL_E2E_PASS" in instruction and "users.keys" in instruction
    assert "Русский" in notes and "English" in notes
    assert "2.10.0" in notes and "2.12.0" in notes and "0038_v2_6_0_platform" in notes
    assert "RELEASE_NOTES_V3_1_2.md" in docs and "INSTALL_STEPS.md" in docs and "RELEASE_NOTES_V3_1_1.md" in docs
    assert '"version": "3.1.2"' in steps
    assert "client-logo" not in ui
