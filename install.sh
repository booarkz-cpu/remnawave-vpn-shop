#!/usr/bin/env bash
#
# Remnawave VPN Shop — автоматическая установка на VDS (Ubuntu/Debian)
# Что делает:
#   1. Обновляет систему
#   2. Устанавливает Docker + Docker Compose (автоматически)
#   3. Клонирует проект (если запущен из пустой папки)
#   4. Создаёт .env из .env.example и интерактивно его заполняет
#   5. Генерирует APP_SECRET и пароли, если пустые
#   6. Собирает и запускает контейнеры
#   7. Настраивает UFW
#   8. НЕ делает git commit/push
#
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[FAIL]${NC} $*" >&2; }

# ---------- Проверки ----------
if [[ $EUID -ne 0 ]]; then
  err "Запускать от root: sudo $0"
  exit 1
fi

if [[ -f /etc/os-release ]]; then
  . /etc/os-release
  if [[ "$ID" != "ubuntu" && "$ID" != "debian" ]]; then
    warn "Тестировалось на Ubuntu/Debian. Ваша ОС: $ID. Продолжаем..."
  fi
fi

# ---------- Настройки ----------
PROJECT_DIR="${PROJECT_DIR:-/opt/remnawave-shop}"
GIT_REPO="${GIT_REPO:-https://github.com/booarkz-cpu/remnawave-vpn-shop.git}"
SKIP_UPGRADE="${SKIP_UPGRADE:-no}"   # yes = не делать apt upgrade

# ============================================================
# 1. Обновление системы
# ============================================================
log "Шаг 1/7: Обновление системы..."
export DEBIAN_FRONTEND=noninteractive
apt update -y

if [[ "$SKIP_UPGRADE" != "yes" ]]; then
  log "  apt upgrade (это может занять несколько минут)..."
  apt upgrade -y || warn "apt upgrade завершился с предупреждениями, продолжаем"
fi

log "  Установка базовых пакетов..."
apt install -y \
  curl wget unzip git ufw ca-certificates gnupg lsb-release \
  openssl jq nano

ok "Система обновлена."

# ============================================================
# 2. Автоматическая установка Docker
# ============================================================
log "Шаг 2/7: Установка Docker..."

if command -v docker >/dev/null 2>&1; then
  ok "Docker уже установлен: $(docker --version)"
else
  log "  Скачивание и запуск официального скрипта get.docker.com..."
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sh /tmp/get-docker.sh
  rm -f /tmp/get-docker.sh

  systemctl enable --now docker
  ok "Docker установлен: $(docker --version)"
fi

# Docker Compose plugin
if docker compose version >/dev/null 2>&1; then
  ok "Docker Compose уже установлен: $(docker compose version)"
else
  log "  Установка docker-compose-plugin..."
  apt install -y docker-compose-plugin
  ok "Docker Compose установлен: $(docker compose version)"
fi

# Проверка, что демон запущен
if ! systemctl is-active --quiet docker; then
  log "  Запуск Docker daemon..."
  systemctl start docker
fi

# ============================================================
# 3. Клонирование проекта
# ============================================================
log "Шаг 3/7: Подготовка проекта в $PROJECT_DIR"

if [[ -f "$PROJECT_DIR/docker-compose.yml" ]]; then
  ok "Проект уже на месте: $PROJECT_DIR"
  cd "$PROJECT_DIR"

  # Обновление, если это git-репозиторий
  if [[ -d .git ]]; then
    log "  git pull (обновление до последней версии)..."
    git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true
    git pull --ff-only || warn "git pull не удался, продолжаем с текущей версией"
  fi
else
  log "  Клонирование $GIT_REPO..."
  mkdir -p "$PROJECT_DIR"
  cd "$PROJECT_DIR"

  # На случай, если в папке остались файлы
  if [[ -n "$(ls -A)" ]]; then
    warn "  Папка $PROJECT_DIR не пуста — пропускаю клонирование"
  else
    git clone "$GIT_REPO" .
  fi
fi

# Ищем docker-compose.yml, если он во вложенной папке
if [[ ! -f docker-compose.yml ]]; then
  FOUND=$(find "$PROJECT_DIR" -maxdepth 3 -name "docker-compose.yml" -print -quit)
  if [[ -n "$FOUND" ]]; then
    PROJECT_DIR=$(dirname "$FOUND")
    cd "$PROJECT_DIR"
    log "  docker-compose.yml найден в $PROJECT_DIR"
  else
    err "docker-compose.yml не найден"
    exit 1
  fi
fi

ok "Проект: $PROJECT_DIR"

# ============================================================
# 4. Создание и настройка .env
# ============================================================
log "Шаг 4/7: Настройка .env"

if [[ -f .env ]]; then
  ok ".env уже существует — оставляю как есть"
  warn "  Если нужно пересоздать: rm .env && sudo ./install.sh"
else
  if [[ -f .env.example ]]; then
    cp .env.example .env
    ok "  Создан .env из .env.example"
  else
    err ".env.example не найден"
    exit 1
  fi

  echo
  log "  Интерактивная настройка (Enter — оставить текущее значение)"

  prompt() {
    local key="$1" desc="$2" secret="${3:-no}" current input
    current=$(grep -E "^${key}=" .env | head -n1 | cut -d= -f2- || true)
    if [[ "$secret" == "yes" ]]; then
      read -rsp "    ${key} (${desc}) [${current}]: " input; echo
    else
      read -rp "    ${key} (${desc}) [${current}]: " input
    fi
    [[ -z "$input" ]] && input="$current"
    [[ -z "$input" ]] && return 0
    local tmp; tmp=$(mktemp)
    awk -v k="$key" -v v="$input" 'BEGIN{FS=OFS="="} $1==k{$0=k"="v} {print}' .env > "$tmp" && mv "$tmp" .env
  }

  prompt "BOT_TOKEN"       "токен бота от @BotFather" yes
  prompt "ADMIN_EMAIL"     "email администратора"
  prompt "ADMIN_PASSWORD"  "пароль администратора (мин. 12 символов)" yes
  prompt "REMNAWAVE_URL"   "URL панели Remnawave"
  prompt "REMNAWAVE_TOKEN" "токен API Remnawave" yes
  prompt "ADMIN_DOMAIN"    "домен админки (localhost если нет)"
  prompt "APP_DOMAIN"      "домен приложения (localhost если нет)"
  prompt "API_DOMAIN"      "домен API (localhost если нет)"

  # Автогенерация секретов
  if grep -qE "^APP_SECRET=$|^APP_SECRET=change" .env; then
    RAND=$(openssl rand -hex 32)
    sed -i "s|^APP_SECRET=.*|APP_SECRET=${RAND}|" .env
    ok "  APP_SECRET сгенерирован"
  fi
  if grep -qE "^DB_PASSWORD=$|^DB_PASSWORD=change" .env; then
    RAND=$(openssl rand -hex 16)
    sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=${RAND}|" .env
    ok "  DB_PASSWORD сгенерирован"
  fi

  chmod 600 .env
  ok "  .env настроен и защищён (chmod 600)"
fi

# ============================================================
# 5. Сборка и запуск
# ============================================================
log "Шаг 5/7: Сборка и запуск контейнеров (займёт 3–7 минут)..."
docker compose pull || true
docker compose up -d --build

log "  Ожидание 20 секунд для старта сервисов..."
sleep 20

# ============================================================
# 6. Проверка
# ============================================================
log "Шаг 6/7: Проверка статуса"
docker compose ps

if docker compose ps --status running | grep -q "running"; then
  ok "Сервисы запущены"
else
  warn "Не все сервисы запустились. Последние 80 строк логов:"
  docker compose logs --tail=80
fi

# ============================================================
# 7. Firewall
# ============================================================
log "Шаг 7/7: Настройка UFW"
if command -v ufw >/dev/null 2>&1; then
  ufw allow 22/tcp  || true
  ufw allow 80/tcp  || true
  ufw allow 443/tcp || true
  ufw --force enable || true
  ok "UFW: разрешены порты 22, 80, 443"
fi

# ============================================================
# Итог
# ============================================================
echo
echo "====================================================="
ok "Установка Remnawave VPN Shop завершена"
echo "====================================================="
echo " Проект  : $PROJECT_DIR"
echo " Статус  : docker compose ps"
echo " Логи    : docker compose logs -f"
echo " Рестарт : docker compose restart"
echo " Стоп    : docker compose down"
echo " Обновл. : git pull && docker compose up -d --build"
echo "====================================================="
