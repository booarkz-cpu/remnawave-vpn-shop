from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_release_identity_and_migration_head():
    main = (ROOT / "backend/app/main.py").read_text()
    build = (ROOT / "scripts/build-release.sh").read_text()
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    manifest = (ROOT / "release-manifest.template.json").read_text()
    assert 'APP_VERSION = "3.0.0-realise"' in main
    assert 'APP_VERSION = "2.13.0"' in main
    assert 'APP_VERSION = "2.12.0"' in main
    assert 'APP_VERSION = "2.11.0"' in main
    assert 'APP_VERSION = "2.10.0"' in main
    assert 'APP_VERSION = "2.9.0"' in main
    assert 'APP_VERSION = "2.8.0"' in main
    assert 'APP_VERSION = "2.7.0"' in main
    assert 'APP_VERSION = "2.6.0"' in main
    assert 'APP_VERSION = "2.5.0"' in main
    assert 'APP_VERSION = "2.4.0"' in main
    assert 'APP_VERSION = "2.3.0"' in main
    assert 'APP_VERSION = "2.2.1"' in main
    assert 'VERSION="3.0.0-realise"' in build
    assert 'VERSION="2.13.0"' in build
    assert 'VERSION="2.12.0"' in build
    assert 'VERSION="2.11.0"' in build
    assert 'VERSION="2.10.0"' in build
    assert 'VERSION="2.9.0"' in build
    assert 'VERSION="2.8.0"' in build
    assert 'VERSION="2.7.0"' in build
    assert 'VERSION="2.6.0"' in build
    assert 'VERSION="2.5.0"' in build
    assert 'VERSION="2.4.0"' in build
    assert 'VERSION="2.3.0"' in build
    assert 'INSTALLER_VERSION="3.0.0-realise"' in installer
    assert 'INSTALLER_VERSION="2.13.0"' in installer
    assert 'INSTALLER_VERSION="2.12.0"' in installer
    assert 'INSTALLER_VERSION="2.11.0"' in installer
    assert 'INSTALLER_VERSION="2.10.0"' in installer
    assert 'INSTALLER_VERSION="2.9.0"' in installer
    assert 'INSTALLER_VERSION="2.8.0"' in installer
    assert 'INSTALLER_VERSION="2.7.0"' in installer
    assert 'INSTALLER_VERSION="2.6.0"' in installer
    assert 'INSTALLER_VERSION="2.5.0"' in installer
    assert 'INSTALLER_VERSION="2.4.0"' in installer
    assert 'INSTALLER_VERSION="2.3.0"' in installer
    assert '"version": "3.0.0-realise"' in manifest
    assert '"version": "2.13.0"' in manifest
    assert '"version": "2.12.0"' in manifest
    assert '"version": "2.11.0"' in manifest
    assert '"version": "2.10.0"' in manifest
    assert '"version": "2.9.0"' in manifest
    assert '"version": "2.8.0"' in manifest
    assert '"version": "2.7.0"' in manifest
    assert '"version": "2.6.0"' in manifest
    assert '"version": "2.5.0"' in manifest
    assert '"version": "2.4.0"' in manifest
    assert '"version": "2.3.0"' in manifest
    assert '0038_v2_6_0_platform' in build
    assert '0037_v2_5_0_tariff_constructor' in build
    assert '0036_v2_4_0_cabinet' in build
    assert '0035_v2_3_0_wallet_gifts' in build


def test_release_tooling_uses_current_artifact():
    verify = (ROOT / "scripts/verify-release.sh").read_text()
    build = (ROOT / "scripts/build-release.sh").read_text()
    artifact = "remnawave_vpn_shop_v2_6_0_full_release.zip"
    assert "${ARTIFACT%.zip}_manifest.json" in verify
    assert 'ARTIFACT="remnawave_vpn_shop_v3_0_0_realise_full_release.zip"' in build
    assert 'ARTIFACT="remnawave_vpn_shop_v2_13_0_full_release.zip"' in build
    assert 'ARTIFACT="remnawave_vpn_shop_v2_12_0_full_release.zip"' in build
    assert 'ARTIFACT="remnawave_vpn_shop_v2_11_0_full_release.zip"' in build
    assert 'ARTIFACT="remnawave_vpn_shop_v2_10_0_full_release.zip"' in build
    assert 'ARTIFACT="remnawave_vpn_shop_v2_9_0_full_release.zip"' in build
    assert 'ARTIFACT="remnawave_vpn_shop_v2_8_0_full_release.zip"' in build
    assert 'ARTIFACT="remnawave_vpn_shop_v2_7_0_full_release.zip"' in build
    assert 'ARTIFACT="remnawave_vpn_shop_v2_6_0_full_release.zip"' in build
    assert 'ARTIFACT="remnawave_vpn_shop_v2_5_0_full_release.zip"' in build
    assert "remnawave_vpn_shop_v2_4_0_full_release.zip" in build
    assert "remnawave_vpn_shop_v40_production.zip" not in verify


def test_financial_ledger_is_immutable_and_idempotent_by_database_contract():
    migration = (ROOT / "backend/alembic/versions/0034_v2_2_0_platform_features.py").read_text()
    models = (ROOT / "backend/app/models.py").read_text()
    main = (ROOT / "backend/app/main.py").read_text()
    assert 'notifications' in migration
    assert 'status_components' in migration
    assert 'deployments' in migration
    assert 'class FinancialLedger(Base):' in models
    assert 'ON CONFLICT (operation_key) DO NOTHING' in main
    assert 'class Notification(Base):' in models
    assert 'class StatusComponent(Base):' in models


def test_request_tracing_and_health_endpoints_exist():
    main = (ROOT / "backend/app/main.py").read_text()
    assert 'X-Request-ID' in main
    assert 'request_id' in main
    assert '@app.get("/health/live")' in main
    assert '@app.get("/health/ready")' in main
    assert '_BACKGROUND_TASKS' in main


def test_v220_platform_features_are_present_and_guarded():
    models=(ROOT/"backend/app/models.py").read_text(); main=(ROOT/"backend/app/main.py").read_text(); migration=(ROOT/"backend/alembic/versions/0034_v2_2_0_platform_features.py").read_text(); security=(ROOT/"backend/app/security.py").read_text()
    assert "class Notification(Base):" in models
    assert "class StatusComponent(Base):" in models
    assert "class Deployment(Base):" in models
    assert "first_purchase_only" in models and "max_uses_per_user" in models and "referral_only" in models
    assert '@app.get("/api/public/status")' in main
    assert '@app.post("/api/admin/deployments/{deployment_id}/promote")' in main
    assert 'error_rate_percent >= Decimal("5")' in main
    assert 'ops.releases' in security
    assert '0034_v2_2_0_platform_features' in migration
