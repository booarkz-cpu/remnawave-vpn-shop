#!/usr/bin/env bash
# Build sideload debug APKs for the buyer and administrator Android apps.
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
for app in android-user android-admin; do
  dir="$ROOT/mobile/$app"
  if [[ "$GRADLE" == "$ROOT/mobile/android-user/gradlew" ]]; then
    (cd "$dir" && "$dir/gradlew" :app:assembleDebug --no-daemon)
  else
    (cd "$dir" && "$GRADLE" :app:assembleDebug --no-daemon)
  fi
  src="$dir/app/build/outputs/apk/debug/app-debug.apk"
  name="remnawave_vpn_shop_${app//-/_}_2_9_0.apk"
  cp "$src" "$OUT/$name"
  sha256sum "$OUT/$name" > "$OUT/$name.sha256"
  echo "APK: $OUT/$name"
done
