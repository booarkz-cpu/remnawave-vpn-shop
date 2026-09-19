#!/usr/bin/env bash
set -Eeuo pipefail
APP_DIR="${APP_DIR:-/opt/vpn-shop}"
cd "$APP_DIR"
echo "Для production используйте Admin → Бекапы: там настраиваются расписание, шифрование, retention и создаётся полный backup."
echo "Проверка контейнеров:"
docker compose ps
