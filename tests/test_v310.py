"""3.1.0 audit, checksum and install-guide contracts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUYER_APK = "https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.10.0/remnawave_vpn_shop_android_user_2_10_0.apk"
ADMIN_APK = "https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.12.0/remnawave_vpn_shop_android_admin_2_12_0.apk"


def test_release_310_is_current_and_documented():
    main = (ROOT / "backend/app/main.py").read_text()
    notes = (ROOT / "RELEASE_NOTES_V3_1_0.md").read_text()
    readme = (ROOT / "README.md").read_text()
    security = (ROOT / "SECURITY.md").read_text()
    instruction = (ROOT / "INSTRUCTION.md").read_text()
    assert main.index('APP_VERSION = "3.1.0"') < main.index('APP_VERSION = "3.0.1"')
    assert main.index('APP_VERSION = "3.0.1"') < main.index('APP_VERSION = "3.0.0-realise"')
    assert "3.1.0" in notes and "Русский" in notes and "English" in notes
    assert "3.0.1" in notes and "3.0.0-realise" in readme
    assert BUYER_APK in readme and ADMIN_APK in readme
    assert "Как скачать приложения для Android и iOS" in readme
    assert "How to download the Android and iOS apps" in readme
    assert "sha256sum -c" in readme and "mobile/ios-user" in readme and "mobile/ios-admin" in readme
    assert "3.1.0" in security and "safe_sha256" in security
    assert "9.14" in instruction
    assert "личный кабинет" in readme and "Конструктор тарифов" in readme


def test_public_plans_and_auto_renew_do_not_leak_internals():
    main = (ROOT / "backend/app/main.py").read_text()
    plans = main[main.index("async def plans"): main.index("async def validate_promo")]
    assert "remnawave_profile_id" not in plans
    admin = main[main.index("async def admin_list_plans"): main.index("async def create_plan")]
    assert '"remnawave_profile_id":p.remnawave_profile_id' in admin
    status = main[main.index("async def auto_renew_status"): main.index("async def connection_qr")]
    assert "method.last_error if method else None" not in status
    assert "Автопродление не выполнено" in status
    file_route = main[main.index("async def subscription_file"): main.index("async def connection_info")]
    assert 'filename="remnawave-subscription.txt"' in file_route
    assert "private, no-store" in file_route
    assert "\\r\\n\\x00" in file_route


def test_install_guide_and_package_checksum():
    catalog = (ROOT / "backend/app/mobile_catalog.py").read_text()
    assert catalog.index("async def public_install_guide") < catalog.index("async def public_app_download")
    assert BUYER_APK in catalog and ADMIN_APK in catalog
    assert 'card["file_sha256"] = digest' in catalog
    assert "def safe_sha256" in catalog
    cabinet = (ROOT / "cabinet/src/main.tsx").read_text()
    admin = (ROOT / "admin/src/main.tsx").read_text()
    assert "Скачать подписку" in cabinet and "/api/me/subscription-file" in cabinet
    assert "Контрольная сумма" in cabinet and "Контрольная сумма" in admin
    assert "client-logo" not in admin
    assert "Скачать подписку" in (ROOT / "cabinet/src/i18n.tsx").read_text()
    assert "Контрольная сумма" in (ROOT / "admin/src/i18n.tsx").read_text()
