#!/usr/bin/env bash
#
# Remnawave VPN Shop — установка на VDS (Ubuntu/Debian)
# Этот скрипт НЕ делает git push/commit. Только установка.
#
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[FAIL]${NC} $*" >&2; }

if [[ $EUID -ne 0 ]]; then
  err "Запускать от root: sudo $0"
  exit 1
fi

PROJECT_DIR="${PROJECT_DIR:-/opt/remnawave-shop}"
cd "$PROJECT_DIR" 2>/dev/null || { err "Папка $PROJECT_DIR не найдена"; exit 1; }

# --- 1. Docker ---
if ! command -v docker >/dev/null 2>&1; then
  log "Установка Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
  ok "Docker: $(docker --version)"
else
  ok "Docker уже есть"
fi

if ! docker compose version >/dev/null 2>&1; then
  log "Установка Docker Compose plugin..."
  apt install -y docker-compose-plugin
fi
ok "Docker Compose: $(docker compose version)"

# --- 2. .env ---
if [[ -f .env ]]; then
  ok ".env уже существует — пропускаем"
else
  if [[ -f .env.example ]]; then
    cp .env.example .env
    chmod 600 .env
    ok "Создан .env из .env.example"
  else
    err ".env.example не найден"
    exit 1
  fi

  log "Настройка .env"
  prompt() {
    local key="$1" desc="$2" secret="${3:-no}" current input
    current=$(grep -E "^${key}=" .env | head -n1 | cut -d= -f2- || true)
    if [[ "$secret" == "yes" ]]; then
      read -rsp "  ${key} (${desc}) [${current}]: " input; echo
    else
      read -rp "  ${key} (${desc}) [${current}]: " input
    fi
    [[ -z "$input" ]] && input="$current"
    [[ -z "$input" ]] && return 0
    local tmp; tmp=$(mktemp)
    awk -v k="$key" -v v="$input" 'BEGIN{FS=OFS="="} $1==k{$0=k"="v} {print}' .env > "$tmp" && mv "$tmp" .env
  }

  prompt "BOT_TOKEN"      "токен бота от @BotFather" yes
  prompt "ADMIN_EMAIL"    "email администратора"
  prompt "ADMIN_PASSWORD" "пароль администратора" yes
  prompt "REMNAWAVE_URL"  "URL панели Remnawave"
  prompt "REMNAWAVE_TOKEN" "токен API Remnawave" yes
  prompt "ADMIN_DOMAIN"   "домен админки (localhost если нет домена)"
  prompt "APP_DOMAIN"     "домен приложения (localhost если нет домена)"
  prompt "API_DOMAIN"     "домен API (localhost если нет домена)"

  if grep -qE "^APP_SECRET=$|^APP_SECRET=change" .env; then
    RAND=$(openssl rand -hex 32)
    sed -i "s|^APP_SECRET=.*|APP_SECRET=${RAND}|" .env
    ok "APP_SECRET сгенерирован"
  fi

  chmod 600 .env
  ok ".env настроен"
fi

# --- 3. Запуск ---
log "Сборка и запуск контейнеров..."
docker compose pull || true
docker compose up -d --build
sleep 20

docker compose ps

if docker compose ps --status running | grep -q "running"; then
  ok "Сервисы запущены"
else
  warn "Не все сервисы поднялись. Логи:"
  docker compose logs --tail=80
fi

# --- 4. Firewall ---
if command -v ufw >/dev/null 2>&1; then
  ufw allow 22/tcp  || true
  ufw allow 80/tcp  || true
  ufw allow 443/tcp || true
  ufw --force enable || true
  ok "UFW настроен"
fi

echo
echo "====================================================="
ok "Установка завершена"
echo " Проверка: cd $PROJECT_DIR && docker compose ps"
echo " Логи    : docker compose logs -f"
echo "====================================================="
