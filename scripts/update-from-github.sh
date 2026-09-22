#!/usr/bin/env bash
# Download the newest GitHub release, verify SHA-256, keep .env, then run update.sh.
# update.sh snapshots the current install before it copies UPDATE_STAGE.
# Cron is not installed by this script.
set -Eeuo pipefail
APP_DIR="${APP_DIR:-/opt/vpn-shop}"
cd "$APP_DIR"
[[ -f .env ]] || { echo "Missing $APP_DIR/.env" >&2; exit 2; }
STAGE="$(mktemp -d)"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT
set +e
LATEST="$(python3 "$APP_DIR/scripts/github_release_fetch.py" "$APP_DIR" "$STAGE")"
status=$?
set -e
if [[ "$status" -ne 0 ]]; then
  echo "$LATEST" >&2
  exit "$status"
fi
if [[ "$LATEST" == Установлена* ]]; then
  echo "$LATEST"
  exit 0
fi
export UPDATE_STAGE="$STAGE"
trap - EXIT
echo "Проверен релиз $LATEST. Снимок текущей установки делает update.sh, затем он заменяет файлы."
exec bash "$APP_DIR/scripts/update.sh"
