import json
from pathlib import Path

import mobile.client_rules as rules

ROOT = Path(__file__).resolve().parents[1]


def test_mobile_base_and_node_rules():
    assert rules.normalize_base("https://api.example.com/") == "https://api.example.com"
    assert rules.normalize_base("http://10.0.2.2:8000") == "http://10.0.2.2:8000"
    for bad in ("http://shop.example.com", "https://user:pass@api.example.com", "ftp://api.example.com", ""):
        try:
            rules.normalize_base(bad)
        except ValueError:
            continue
        raise AssertionError(bad)
    node = rules.public_node({"name": "203.0.113.10", "status": "online", "users_online": 3, "address": "secret"})
    assert node == {"name": "node", "country": "", "status": "online", "users_online": 3}
    assert "address" not in node
    assert rules.error_detail('{"detail":"Доступ ограничен"}', 403) == "Доступ ограничен"
    assert rules.error_detail("not-json", 500) == "HTTP 500"


def test_mobile_catalogs_are_complete_and_copied():
    for name in ("user", "admin"):
        catalog = json.loads((ROOT / f"mobile/l10n/{name}.json").read_text())
        assert set(catalog) == {"ru", "en"}
        assert catalog["ru"].keys() == catalog["en"].keys()
        assert all(catalog["ru"].values()) and all(catalog["en"].values())
    assert (ROOT / "mobile/android-user/app/src/main/assets/l10n.json").read_text() == (ROOT / "mobile/l10n/user.json").read_text()
    assert (ROOT / "mobile/android-admin/app/src/main/assets/l10n.json").read_text() == (ROOT / "mobile/l10n/admin.json").read_text()
    assert (ROOT / "mobile/ios-user/VpnShopUser/l10n.json").read_text() == (ROOT / "mobile/l10n/user.json").read_text()
    assert (ROOT / "mobile/ios-admin/VpnShopAdmin/l10n.json").read_text() == (ROOT / "mobile/l10n/admin.json").read_text()


def test_native_clients_keep_session_bounds():
    user_android = (ROOT / "mobile/android-user/app/src/main/java/shop/remnawave/user/MainActivity.kt").read_text()
    admin_android = (ROOT / "mobile/android-admin/app/src/main/java/shop/remnawave/admin/MainActivity.kt").read_text()
    user_ios = (ROOT / "mobile/ios-user/VpnShopUser/VpnShopUserApp.swift").read_text()
    admin_ios = (ROOT / "mobile/ios-admin/VpnShopAdmin/VpnShopAdminApp.swift").read_text()
    for source, client in (
        (user_android, "android-user"),
        (admin_android, "android-admin"),
        (user_ios, "ios-user"),
        (admin_ios, "ios-admin"),
    ):
        assert client in source
        assert "Bearer" in source
        assert "instanceFollowRedirects = false" in source or "completionHandler(nil)" in source
        assert "10.0.2.2" in source
        assert "Log." not in source
        assert "println(token" not in source
    assert "X-Shop-Client" in user_android and "X-Shop-Client" in admin_android
    assert "Idempotency-Key" in user_android
    assert "device_option_id" in user_android
    assert "/api/admin/platform/summary" in admin_android
    assert "publicNode" in user_android and "publicNode" in admin_ios
    auth = (ROOT / "backend/app/mobile_auth.py").read_text()
    cabinet = (ROOT / "backend/app/cabinet_api.py").read_text()
    main = (ROOT / "backend/app/main.py").read_text()
    assert "android-user" in auth and "ios-admin" in auth
    assert "session_body" in cabinet and "session_body" in main
    assert 'APP_VERSION = "2.7.0"' in main
    assert "LicenseRef-Proprietary" in (ROOT / "mobile/LICENSE").read_text()
    assert "Android и iOS" in (ROOT / "LICENSE").read_text()


def test_localization_covers_mobile_and_web_patterns():
    cabinet = (ROOT / "cabinet/src/i18n.tsx").read_text()
    mini = (ROOT / "miniapp/src/i18n.tsx").read_text()
    admin = (ROOT / "admin/src/i18n.tsx").read_text()
    assert 'aria-label' in cabinet and 'aria-label' in mini and 'aria-label' in admin
    assert "Онлайн" in cabinet and "Online ${online[1]} of ${online[2]}" in cabinet
    assert "Online ${online[1]} of ${online[2]}" in mini
    notes = (ROOT / "RELEASE_NOTES_V2_7_0.md").read_text()
    mobile = (ROOT / "MOBILE.md").read_text()
    assert "2.7.0" in notes and "Android" in notes and "iOS" in notes
    assert "Русский" in mobile and "English" in mobile
    assert "9.6" in (ROOT / "INSTRUCTION.md").read_text()
