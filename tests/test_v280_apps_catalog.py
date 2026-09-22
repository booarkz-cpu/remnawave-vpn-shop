from pathlib import Path

from backend.app.mobile_catalog import card_from_input, parse_catalog, public_cards, safe_media_path

ROOT = Path(__file__).resolve().parents[1]


def test_app_catalog_hides_admin_cards_and_rejects_unsafe_values():
    cards = parse_catalog(None)
    public = public_cards(cards)
    assert [row["id"] for row in public] == ["android-user", "ios-user"]
    assert all(row["audience"] == "user" and row["enabled"] for row in public)
    assert safe_media_path("/media/branding-client-logo-abc.png") == "/media/branding-client-logo-abc.png"
    assert safe_media_path("/media/../secret.png") == ""
    assert safe_media_path("https://evil.example/logo.png") == ""
    saved = card_from_input({"id": "android-user", "enabled": False, "title_ru": "Магазин", "url": "https://play.google.com/store/apps/details?id=shop"})
    assert saved["enabled"] is False
    assert saved["audience"] == "user"
    assert saved["url"].startswith("https://")
    for bad in ("http://shop.example/app", "https://user:pass@shop.example/app", "https://127.0.0.1/app", "javascript:alert(1)"):
        try:
            card_from_input({"id": "ios-user", "url": bad})
        except ValueError:
            continue
        raise AssertionError(bad)


def test_admin_and_cabinet_expose_app_catalog():
    admin = (ROOT / "admin/src/main.tsx").read_text()
    cabinet = (ROOT / "cabinet/src/main.tsx").read_text()
    main = (ROOT / "backend/app/main.py").read_text()
    user_android = (ROOT / "mobile/android-user/app/src/main/java/shop/remnawave/user/MainActivity.kt").read_text()
    admin_android = (ROOT / "mobile/android-admin/app/src/main/java/shop/remnawave/admin/MainActivity.kt").read_text()
    assert 'APP_VERSION = "2.8.0"' in main
    assert "from __future__ import annotations" in main
    assert "apps_router" in main
    assert "/api/admin/apps" in admin and "Приложения" in admin and "client-logo" not in admin
    assert "/api/admin/apps/logo" in admin
    assert "/api/public/apps" in cabinet and "Приложения" in cabinet
    assert "/api/public/apps" in user_android and "safeMediaPath" in user_android
    assert "/api/admin/apps" in admin_android and "safeMediaPath" in admin_android
    assert "safeMediaPath" in (ROOT / "mobile/ios-user/VpnShopUser/VpnShopUserApp.swift").read_text()
    assert "/api/admin/apps" in (ROOT / "mobile/ios-admin/VpnShopAdmin/ContentView.swift").read_text()
    notes = (ROOT / "RELEASE_NOTES_V2_8_0.md").read_text()
    assert "2.8.0" in notes and "логотип" in notes.lower()
    assert "9.7" in (ROOT / "INSTRUCTION.md").read_text()
