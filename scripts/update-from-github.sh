#!/usr/bin/env bash
# Download the newest GitHub release, verify SHA-256, keep .env, then run update.sh.
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
# The release zip contains the repository root. Copy it over the install
# without replacing secrets or the rollback archive.
tar --exclude='./.env' --exclude='./.env.*' --exclude='./.rollback' --exclude='./.git' -C "$STAGE" -cf - . | tar -C "$APP_DIR" -xf -
echo "Файлы релиза $LATEST разложены. Запуск update.sh"
exec bash "$APP_DIR/scripts/update.sh"
