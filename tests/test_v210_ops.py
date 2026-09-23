"""Source contracts for the 2.10.0 buyer and operator features."""
import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import mobile.client_rules as rules

ROOT = Path(__file__).resolve().parents[1]


def _fetch_module():
    spec = importlib.util.spec_from_file_location("github_release_fetch", ROOT / "scripts/github_release_fetch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_client_proof_matches_backend_and_known_shape():
    sys.path.insert(0, str(ROOT / "backend"))
    from app.mobile_auth import client_proof as api_proof

    message = rules.proof_message("android-user", "1700000000", "get", "/api/me/devices")
    assert message == "android-user\n1700000000\nGET\n/api/me/devices"
    left = rules.client_proof("android-user", "1700000000", "GET", "/api/me/devices")
    right = api_proof(rules.MOBILE_CLIENT_KEY, "android-user", "1700000000", "get", "/api/me/devices")
    assert left == right
    assert len(left) == 64
    assert left == left.lower()


def test_subscription_links_and_stale_agents():
    apps = rules.subscription_apps("https://shop.example/sub/abc")
    assert set(apps) == {"happ", "v2rayng", "streisand"}
    assert apps["happ"].startswith("happ://add/")
    assert apps["v2rayng"].startswith("v2rayng://install-sub?url=")
    assert apps["streisand"].startswith("streisand://import/")
    assert rules.subscription_apps("http://shop.example/sub") == {}
    assert rules.subscription_apps("https://shop.example/a b") == {}
    assert rules.agent_is_stale(None) is True
    assert rules.agent_is_stale(datetime(2026, 1, 1, 0, 0), datetime(2026, 1, 1, 0, 6)) is True
    assert rules.agent_is_stale(datetime(2026, 1, 1, 0, 4), datetime(2026, 1, 1, 0, 6)) is False
    assert rules.agent_is_stale("2026-01-01T00:00:00Z", datetime(2026, 1, 1, 0, 6)) is True


def test_routes_and_release_scripts():
    main = (ROOT / "backend/app/main.py").read_text()
    devices = main[main.index("async def my_devices"):main.index("class DeviceRegisterIn")]
    assert "device_key" not in devices and "last_ip" not in devices
    assert '@app.post("/api/admin/plans/{plan_id}/enabled")' in main
    assert '@app.get("/api/admin/payments/{payment_id}")' in main
    assert '@app.get("/api/admin/github-update")' in main
    assert 'APP_VERSION = "3.0.0-realise"' in main
    assert 'APP_VERSION = "2.13.0"' in main
    assert 'APP_VERSION = "2.12.0"' in main
    assert 'APP_VERSION = "2.11.0"' in main
    assert 'APP_VERSION = "2.10.0"' in main
    config = (ROOT / "backend/app/config.py").read_text()
    assert "MOBILE_REQUIRE_PROOF" in config and "MOBILE_CLIENT_KEY" in config
    platform = (ROOT / "backend/app/platform_api.py").read_text()
    assert '"stale"' in platform
    updater = (ROOT / "scripts/update-from-github.sh").read_text()
    assert "scripts/update.sh" in updater
    assert "UPDATE_STAGE" in updater
    update_sh = (ROOT / "scripts/update.sh").read_text()
    assert "--exclude='./.env'" in update_sh
    assert update_sh.index("pre-update-$STAMP.tar.gz") < update_sh.index("UPDATE_STAGE")
    fetch = (ROOT / "scripts/github_release_fetch.py").read_text()
    assert "sha256" in fetch and "full_release" in fetch
    assert (ROOT / "mobile/android-user/app-release.apk").exists() is False
    notes = (ROOT / "RELEASE_NOTES_V2_10_0.md").read_text()
    assert "2.10.0" in notes and "SHA-256" in notes and "2.9.0" in notes


def test_github_fetcher_rejects_zip_slip(tmp_path):
    module = _fetch_module()
    assert module.version_tuple("v2.10.0") > module.version_tuple("2.9.0")
    assert module.current_version(ROOT) == "3.1.6"
    assert module.version_tuple("3.1.6") > module.version_tuple("3.1.5") > module.version_tuple("3.1.4")
    assert module.version_tuple("3.1.2") > module.version_tuple("3.1.1")
    assert module.version_tuple("3.1.1") > module.version_tuple("3.1.0")
    assert module.version_tuple("3.1.0") > module.version_tuple("3.0.1")
    assert module.version_tuple("3.0.1") > module.version_tuple("3.0.0-realise")
    assert module.version_tuple("3.0.0-realise") > module.version_tuple("2.13.0")
    import io
    import zipfile

    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w") as archive:
        archive.writestr("../escape.txt", "no")
    try:
        module.safe_extract(blob.getvalue(), tmp_path)
    except SystemExit:
        return
    raise AssertionError("zip slip was accepted")


def test_github_fetcher_rejects_symlink(tmp_path):
    import io
    import stat
    import zipfile

    module = _fetch_module()
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w") as archive:
        info = zipfile.ZipInfo("link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "/tmp/outside")
    try:
        module.safe_extract(blob.getvalue(), tmp_path)
    except SystemExit:
        return
    raise AssertionError("symlink archive was accepted")
