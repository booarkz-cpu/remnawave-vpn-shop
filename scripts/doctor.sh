#!/usr/bin/env bash
set -Eeuo pipefail
APP_DIR="${APP_DIR:-/opt/vpn-shop}"
cd "$APP_DIR"
[[ -f .env ]] || { echo "Missing $APP_DIR/.env" >&2; exit 2; }
docker compose config >/dev/null
docker compose ps
echo
if docker compose exec -T backend python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5)' >/dev/null 2>&1; then
  echo "API health: OK"
else
  echo "API health: FAILED"; exit 1
fi
for svc in admin miniapp cabinet; do
  if docker compose exec -T "$svc" curl -fsS http://127.0.0.1/ >/dev/null 2>&1; then
    echo "$svc HTTP: OK"
  else
    echo "$svc HTTP: FAILED"; exit 1
  fi
done
