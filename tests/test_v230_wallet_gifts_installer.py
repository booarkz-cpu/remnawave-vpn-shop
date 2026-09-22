from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_one_step_installer_delegates_and_does_not_publish_app_ports():
    text = (ROOT / "install.sh").read_text()
    assert "deploy/install-vps.sh" in text
    assert "exec bash" in text
    assert "8000/tcp" not in text
    assert "3000/tcp" not in text


def test_vps_installer_collects_operator_settings():
    text = (ROOT / "deploy/install-vps.sh").read_text()
    for key in (
        "BOT_USERNAME",
        "DEFAULT_LANGUAGE",
        "REQUIRED_TELEGRAM_CHANNEL",
        "AUTO_RENEW_LEAD_DAYS",
        "WEBHOOK_BASE_URL",
        "INSTALL_NONINTERACTIVE",
    ):
        assert key in text
    assert "ufw allow 80/tcp" in text
    assert "8000/tcp" not in text


def test_wallet_gifts_and_days_promo_are_wired():
    main = (ROOT / "backend/app/main.py").read_text()
    models = (ROOT / "backend/app/models.py").read_text()
    migration = (ROOT / "backend/alembic/versions/0035_v2_3_0_wallet_gifts.py").read_text()
    assert 'APP_VERSION = "2.3.0"' in main
    assert "async def wallet_topup" in main
    assert "async def wallet_spend" in main
    assert "async def purchase_gift" in main
    assert "Gift purchaser cannot redeem their own gift" in main
    assert 'if kind == "days"' in main
    assert "wallet_balance" in models
    assert "purchaser_user_id" in models
    assert 'revision = "0035_v2_3_0_wallet_gifts"' in migration
    assert 'down_revision = "0034_v2_2_0_platform_features"' in migration


def test_v230_release_markers_remain_as_history():
    main = (ROOT / "backend/app/main.py").read_text()
    assert 'APP_VERSION = "2.4.0"' in main
    assert 'Historical compatibility marker: APP_VERSION = "2.3.0"' in main
