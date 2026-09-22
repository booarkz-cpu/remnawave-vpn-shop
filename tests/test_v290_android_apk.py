from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v290_apk_script_notes_and_clients():
    script = (ROOT / "scripts/build-android-apk.sh").read_text()
    assert "android-user" in script and "android-admin" in script
    assert "2_9_0" in script
    notes = (ROOT / "RELEASE_NOTES_V2_9_0.md").read_text()
    assert "2.9.0" in notes and "APK" in notes
    instruction = (ROOT / "INSTRUCTION.md").read_text()
    assert "9.8" in instruction and "9.7" in instruction and "9.6" in instruction
    mobile = (ROOT / "MOBILE.md").read_text()
    assert "2.9.0" in mobile and "Русский" in mobile and "English" in mobile
    assert "RemnawaveShop-Android-User/2.9.0" in mobile
    user = (ROOT / "mobile/android-user/app/src/main/java/shop/remnawave/user/MainActivity.kt").read_text()
    admin = (ROOT / "mobile/android-admin/app/src/main/java/shop/remnawave/admin/MainActivity.kt").read_text()
    ios_user = (ROOT / "mobile/ios-user/VpnShopUser/VpnShopUserApp.swift").read_text()
    ios_admin = (ROOT / "mobile/ios-admin/VpnShopAdmin/VpnShopAdminApp.swift").read_text()
    assert "externalUrlAllowed" in user
    assert 'RemnawaveShop-Android-User/2.9.0' in user
    assert 'RemnawaveShop-Android-Admin/2.9.0' in admin
    assert 'RemnawaveShop-iOS-User/2.9.0' in ios_user
    assert 'RemnawaveShop-iOS-Admin/2.9.0' in ios_admin
    assert "private let localHttpHosts" not in ios_user
    assert "localHttpHosts" in (ROOT / "mobile/ios-user/VpnShopUser/ContentView.swift").read_text()
    assert 'versionName = "2.9.0"' in (ROOT / "mobile/android-user/app/build.gradle.kts").read_text()
    assert 'versionName = "2.9.0"' in (ROOT / "mobile/android-admin/app/build.gradle.kts").read_text()
    assert "*.apk" in (ROOT / "scripts/build-release.sh").read_text()
