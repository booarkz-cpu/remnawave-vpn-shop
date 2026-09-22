"""2.12.0 Telegram broadcast from the admin panel and the admin apps."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_broadcast_queue_resumes_and_is_exposed():
    bot = (ROOT / "backend/app/bot.py").read_text()
    main = (ROOT / "backend/app/main.py").read_text()
    admin = (ROOT / "admin/src/main.tsx").read_text()
    android = (ROOT / "mobile/android-admin/app/src/main/java/shop/remnawave/admin/MainActivity.kt").read_text()
    ios = (ROOT / "mobile/ios-admin/VpnShopAdmin/ContentView.swift").read_text()
    assert "FOR UPDATE SKIP LOCKED" in bot
    assert "trust_env=False" in bot
    assert "def broadcast_recipient_query" in bot
    assert ".distinct()" in bot
    assert "sent_count" in bot and "failed" in bot
    assert 'status = "failed"' in bot or 'status="failed"' in bot or 'row.status = "failed"' in bot
    assert '@app.post("/api/admin/broadcasts")' in main
    assert '@app.post("/api/admin/broadcasts/{broadcast_id}/retry")' in main
    assert "Caption is longer than 1024 characters" in main
    assert "Button text and URL are set together" in main
    assert "manage_broadcasts" in main
    assert 'target:btarget' in admin or "target:btarget" in admin
    assert "/api/admin/broadcasts/" in admin
    assert "Все с Telegram" in admin and "Активная подписка" in admin
    assert "/api/admin/broadcasts" in android and "/api/admin/marketing" in android
    assert "broadcastTarget" in android
    assert "/api/admin/broadcasts" in ios and "broadcastTarget" in ios
    assert 'APP_VERSION = "2.12.0"' in main
    notes = (ROOT / "RELEASE_NOTES_V2_12_0.md").read_text()
    assert "2.12.0" in notes and "Русский" in notes and "English" in notes
    assert "manage_broadcasts" in notes
