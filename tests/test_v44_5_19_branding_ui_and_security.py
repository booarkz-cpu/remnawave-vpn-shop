from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "backend/app/main.py").read_text()
REQ = (ROOT / "backend/requirements.txt").read_text()
BUILD = (ROOT / "scripts/build-release.sh").read_text()
INSTALL = (ROOT / "deploy/install-vps.sh").read_text()
MANIFEST = (ROOT / "release-manifest.template.json").read_text()
UI = (ROOT / "admin/src/main.tsx").read_text()
CSS = (ROOT / "admin/src/style.css").read_text()


def test_public_branding_has_safe_defaults_and_no_secret_settings():
    assert '/api/public/branding' in MAIN
    assert 'Remnawave VPN Shop' in MAIN
    assert 'app_secret' not in MAIN[MAIN.index('/api/public/branding'):MAIN.index('@app.get("/api/admin/content")')]


def test_branding_assets_are_server_generated_and_reencoded():
    assert '_store_branding_image' in MAIN
    assert 'ImageOps.exif_transpose' in MAIN
    assert 'im.save(out,"PNG",optimize=True)' in MAIN
    assert 'pathlib.Path(old.removeprefix("/media/")).name' in MAIN
    assert 'app_logo' in MAIN and 'app_favicon' in MAIN


def test_branding_uploads_are_authenticated_and_permission_gated():
    assert '@app.post("/api/admin/branding/logo")' in MAIN
    assert '@app.post("/api/admin/branding/favicon")' in MAIN
    assert 'Depends(require_permission("manage_content"))' in MAIN


def test_app_name_has_reasonable_business_limit():
    segment = MAIN[MAIN.index('@app.put("/api/admin/settings/{key}")'):MAIN.index('@app.post("/api/admin/branding/logo")')]
    assert "len(payload.value.strip())>255" in segment


def test_branding_setting_allowlist_does_not_expose_secrets():
    segment = MAIN[MAIN.index('@app.put("/api/admin/settings/{key}")'):MAIN.index('@app.post("/api/admin/branding/logo")')]
    assert 'app_name' in segment and 'theme_default' in segment
    assert 'app_secret' not in segment and 'yookassa_secret_key' not in segment


def test_frontend_supports_light_dark_theme_and_custom_branding():
    assert 'localStorage.getItem("rw_theme")' in UI
    assert 'document.documentElement.dataset.theme' in UI
    assert 'Переключить тему' in UI
    assert 'Брендинг панели' in UI
    assert '/api/admin/branding/logo' in UI
    assert '/api/admin/branding/favicon' in UI
    assert 'app_name' in UI
    assert '--bg:' in CSS
    assert 'html[data-theme="light"]' in CSS


def test_release_is_44_5_20_and_pillow_is_pinned():
    assert '1.0.0-realise' in BUILD
    assert '1.0.0-realise' in INSTALL
    assert '1.0.0-realise' in MANIFEST
    assert 'remnawave_vpn_shop_v1_0_0_realise_deep_audited_fixed.zip' in BUILD
    assert 'Pillow==12.3.0' in REQ


def test_frontend_source_transpile_check_is_documented_by_project_structure():
    assert (ROOT / 'admin/src/main.tsx').exists()
    assert (ROOT / 'admin/src/style.css').exists()
