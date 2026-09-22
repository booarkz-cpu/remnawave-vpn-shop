"""2.13.0 app package uploads and download links."""
import json
from pathlib import Path

from backend.app.mobile_catalog import (
    card_from_input,
    parse_catalog,
    public_cards,
    safe_package_name,
    view_card,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "a" * 32 + ".apk"


def test_package_names_and_public_links_stay_split():
    assert safe_package_name(PACKAGE) == PACKAGE
    assert safe_package_name("../" + PACKAGE) == ""
    assert safe_package_name("/tmp/" + PACKAGE) == ""
    assert safe_package_name("notes.txt") == ""
    saved = card_from_input({"id": "android-admin", "file": PACKAGE, "url": "https://example.com/admin.apk"})
    assert saved["file"] == ""
    assert saved["audience"] == "admin"
    stored = attach_roundtrip()
    public = [view_card(card, public=True) for card in public_cards(stored)]
    assert [row["id"] for row in public] == ["android-user", "ios-user"]
    user = next(row for row in public if row["id"] == "android-user")
    assert user["download_url"] == "/api/public/apps/android-user/download"
    assert "file" not in user
    admin = view_card(next(row for row in stored if row["id"] == "android-admin"), public=False)
    assert admin["download_url"] == "/api/admin/apps/android-admin/download"
    assert admin["has_file"] is True
    hidden = view_card(next(row for row in stored if row["id"] == "ios-admin"), public=True)
    assert hidden["download_url"] == ""


def attach_roundtrip():
    raw = []
    for app_id, name in (("android-user", PACKAGE), ("android-admin", "b" * 32 + ".apk"), ("ios-admin", "not-a-package")):
        raw.append({"id": app_id, "enabled": True, "file": name, "file_label": "pack"})
    return parse_catalog(json.dumps(raw))


def test_panel_and_cabinet_expose_download_links():
    admin = (ROOT / "admin/src/main.tsx").read_text()
    cabinet = (ROOT / "cabinet/src/main.tsx").read_text()
    catalog = (ROOT / "backend/app/mobile_catalog.py").read_text()
    assert "Скачать приложение администратора" in admin
    assert "/api/admin/apps/" in admin and "/file" in admin
    assert "client-logo" not in admin
    assert "android-user|ios-user" in cabinet and "download_url" in cabinet
    assert "Скачать" in cabinet
    assert '@router.post("/api/admin/apps/{app_id}/file")' in catalog
    assert '@router.get("/api/public/apps/{app_id}/download")' in catalog
    assert '@router.get("/api/admin/apps/{app_id}/download")' in catalog
    assert 'audience") != "user"' in catalog
    assert "app-packages" in (ROOT / "backend/app/main.py").read_text()
    notes = (ROOT / "RELEASE_NOTES_V2_13_0.md").read_text()
    assert "2.13.0" in notes and "Русский" in notes and "English" in notes
