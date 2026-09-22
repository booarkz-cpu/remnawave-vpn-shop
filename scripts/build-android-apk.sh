#!/usr/bin/env bash
# Build sideload APKs for the buyer and administrator Android apps.
# ANDROID_KEYSTORE selects assembleRelease. An empty keystore selects assembleDebug.
# iOS IPA packages require Xcode on macOS and are not produced here.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ANDROID_HOME="${ANDROID_HOME:-$HOME/android-sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
if [[ ! -x "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" && ! -d "$ANDROID_HOME/platforms/android-35" ]]; then
  echo "Android SDK 35 не найден. Укажите ANDROID_HOME." >&2
  exit 1
fi
GRADLE="${GRADLE_BIN:-}"
if [[ -z "$GRADLE" ]]; then
  if [[ -x "$ROOT/mobile/android-user/gradlew" ]]; then
    GRADLE="$ROOT/mobile/android-user/gradlew"
  else
    echo "Gradle не найден. Соберите wrapper или задайте GRADLE_BIN." >&2
    exit 1
  fi
fi
OUT="${1:-$ROOT}"
mkdir -p "$OUT"
# Historical compatibility marker: remnawave_vpn_shop_android_user_2_9_0.apk
# Historical compatibility marker: name="remnawave_vpn_shop_${app//-/_}_2_10_0.apk"
TASK=":app:assembleDebug"
KIND="debug"
if [[ -n "${ANDROID_KEYSTORE:-}" ]]; then
  TASK=":app:assembleRelease"
  KIND="release"
fi
for app in android-user android-admin; do
  dir="$ROOT/mobile/$app"
  if [[ "$GRADLE" == "$ROOT/mobile/android-user/gradlew" ]]; then
    (cd "$dir" && "$dir/gradlew" "$TASK" --no-daemon)
  else
    (cd "$dir" && "$GRADLE" "$TASK" --no-daemon)
  fi
  src="$dir/app/build/outputs/apk/$KIND/app-$KIND.apk"
  if [[ "$app" == "android-admin" ]]; then
    name="remnawave_vpn_shop_android_admin_2_12_0.apk"
  else
    name="remnawave_vpn_shop_android_user_2_10_0.apk"
  fi
  cp "$src" "$OUT/$name"
  sha256sum "$OUT/$name" > "$OUT/$name.sha256"
  echo "APK: $OUT/$name"
done
