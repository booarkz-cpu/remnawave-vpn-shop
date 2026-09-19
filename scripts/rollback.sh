#!/usr/bin/env bash
set -Eeuo pipefail
APP_DIR="${APP_DIR:-/opt/vpn-shop}"
ROLLBACK_DIR="${ROLLBACK_DIR:-$APP_DIR/.rollback}"
ARCHIVE="${1:-$ROLLBACK_DIR/latest.tar.gz}"
DB_ARCHIVE="${2:-$ROLLBACK_DIR/latest.sql}"
[[ -f "$ARCHIVE" ]] || { echo "Rollback archive not found: $ARCHIVE" >&2; exit 2; }
cd "$APP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
tar --exclude='./.rollback' --exclude='./.git' --exclude='./.env' --exclude='./.env.*' -czf "$ROLLBACK_DIR/pre-rollback-$STAMP.tar.gz" .
touch "$ROLLBACK_DIR/RECOVERY_MODE"
docker compose down --remove-orphans || true
tmp="$(mktemp -d)"
tar -xzf "$ARCHIVE" -C "$tmp"
find "$APP_DIR" -mindepth 1 -maxdepth 1 ! -name '.env' ! -name '.rollback' -exec rm -rf {} +
cp -a "$tmp"/. "$APP_DIR"/
rm -rf "$tmp"
[[ -s "$DB_ARCHIVE" ]] || { echo "Database snapshot is required for a safe rollback." >&2; exit 1; }
docker compose up -d db redis
cat "$DB_ARCHIVE" | docker compose exec -T db psql -U vpnshop -d vpnshop -v ON_ERROR_STOP=1
./deploy/build-production.sh
./scripts/doctor.sh
rm -f "$ROLLBACK_DIR/RECOVERY_MODE"
printf 'Rollback completed from %s (database: %s)\n' "$ARCHIVE" "$DB_ARCHIVE"
