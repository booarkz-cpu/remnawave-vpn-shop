#!/usr/bin/env bash
#
# Remnawave VPN Shop — полная установка на VPS в один шаг
#
# Использование:
#   curl -fsSL https://raw.githubusercontent.com/booarkz-cpu/remnawave-vpn-shop/main/install.sh | sudo bash
#
# Скрипт:
#   1. Полностью обновляет систему
#   2. Устанавливает Docker + Compose
#   3. Открывает все нужные порты (автоматически)
#   4. Клонирует проект
#   5. Генерирует секреты и .env
#   6. Запускает контейнеры
#   7. Проверяет здоровье сервисов
#
# Идемпотентен: можно запускать повторно.
#
set -euo pipefail

# ============================================================
# ЦВЕТА
# ============================================================
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[FAIL]${NC} $*" >&2; }
step() { echo -e "\n${CYAN}${BOLD}━━━━━━ $* ━━━━━━${NC}\n"; }

# ============================================================
# НАСТРОЙКИ
# ============================================================
REPO_URL="${REPO_URL:-https://github.com/booarkz-cpu/remnawave-vpn-shop.git}"
PROJECT_DIR="${PROJECT_DIR:-/opt/remnawave-shop}"
BRANCH="${BRANCH:-main}"

# Порты по умолчанию — будут дополнены автоматически из docker-compose.yml
DEFAULT_PORTS=(22 80 443 3000 8000 8080 8443)

# ============================================================
# ПРОВЕРКИ
# ============================================================
if [[ $EUID -ne 0 ]]; then
    err "Запускать от root: sudo bash $0"
    exit 1
fi

if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    [[ "$ID" != "ubuntu" && "$ID" != "debian" ]] && \
        warn "Тестировалось на Ubuntu/Debian. Ваша ОС: $ID"
fi

# ============================================================
# 1. СИСТЕМА — ПОЛНОЕ ОБНОВЛЕНИЕ
# ============================================================
step "1/8. ПОЛНОЕ ОБНОВЛЕНИЕ СИСТЕМЫ"

export DEBIAN_FRONTEND=noninteractive

log "apt update..."
apt update -y

log "apt full-upgrade (может занять 2–5 минут)..."
apt full-upgrade -y || warn "apt full-upgrade завершился с предупреждениями"

log "apt autoremove + autoclean..."
apt autoremove -y || true
apt autoclean -y || true

log "Установка базовых пакетов..."
apt install -y \
    curl wget git unzip nano vim ufw openssl jq \
    ca-certificates gnupg lsb-release apt-transport-https \
    htop net-tools dnsutils

ok "Система обновлена полностью"

# ============================================================
# 2. DOCKER
# ============================================================
step "2/8. УСТАНОВКА DOCKER"

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    ok "Docker уже установлен: $(docker --version)"
else
    log "Скачивание и запуск get.docker.com..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh
    rm -f /tmp/get-docker.sh

    if ! docker compose version >/dev/null 2>&1; then
        apt install -y docker-compose-plugin
    fi

    systemctl enable --now docker
    ok "Docker установлен: $(docker --version)"
fi

if ! systemctl is-active --quiet docker; then
    systemctl start docker
    sleep 3
fi

# ============================================================
# 3. ПРОЕКТ
# ============================================================
step "3/8. ПОЛУЧЕНИЕ ПРОЕКТА"

if [[ -f "$PROJECT_DIR/docker-compose.yml" ]]; then
    ok "Проект уже в $PROJECT_DIR"
    cd "$PROJECT_DIR"
    if [[ -d .git ]]; then
        git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true
        log "git pull..."
        git pull --ff-only origin "$BRANCH" || warn "git pull не удался"
    fi
else
    log "Клонирование $REPO_URL в $PROJECT_DIR..."
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    if [[ -n "$(ls -A 2>/dev/null)" ]]; then
        warn "Папка не пуста — очищаю"
        rm -rf "$PROJECT_DIR"/* "$PROJECT_DIR"/.[!.]* 2>/dev/null || true
    fi
    git clone --branch "$BRANCH" "$REPO_URL" .
fi

# Поиск docker-compose.yml во вложенных папках
if [[ ! -f docker-compose.yml ]]; then
    FOUND=$(find "$PROJECT_DIR" -maxdepth 3 -name "docker-compose.yml" -print -quit)
    if [[ -n "$FOUND" ]]; then
        PROJECT_DIR=$(dirname "$FOUND")
        cd "$PROJECT_DIR"
    else
        err "docker-compose.yml не найден"
        exit 1
    fi
fi

ok "Проект: $PROJECT_DIR"

# ============================================================
# 4. .ENV
# ============================================================
step "4/8. НАСТРОЙКА .ENV"

set_var() {
    local key="$1" val="$2"
    if grep -qE "^${key}=" .env 2>/dev/null; then
        local escaped
        escaped=$(printf '%s' "$val" | sed -e 's/[\/&|]/\\&/g')
        sed -i "s|^${key}=.*|${key}=${escaped}|" .env
    else
        echo "${key}=${val}" >> .env
    fi
}

if [[ -f .env ]]; then
    ok ".env уже существует — пропускаю генерацию"
    warn "Изменить: nano $PROJECT_DIR/.env && docker compose restart"
else
    if [[ ! -f .env.example ]]; then
        err ".env.example не найден"
        exit 1
    fi

    cp .env.example .env
    chmod 600 .env

    # Автогенерация секретов
    APP_SECRET=$(openssl rand -hex 32)
    DB_PASS=$(openssl rand -hex 16)

    set_var APP_SECRET "$APP_SECRET"
    set_var DB_PASSWORD "$DB_PASS"
    set_var POSTGRES_PASSWORD "$DB_PASS"
    set_var DATABASE_URL "postgresql+asyncpg://vpnshop:${DB_PASS}@db:5432/vpnshop"
    set_var APP_ENV "production"
    set_var LOG_LEVEL "INFO"

    # IP-адрес сервера
    SERVER_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "localhost")
    set_var PUBLIC_BASE_URL "http://${SERVER_IP}"
    set_var MINI_APP_URL "http://${SERVER_IP}"

    ok "Секреты сгенерированы, IP: $SERVER_IP"

    # --- Интерактивный ввод ---
    echo
    echo "  ┌─────────────────────────────────────────────┐"
    echo "  │  Заполните параметры (Enter — пропустить)   │"
    echo "  └─────────────────────────────────────────────┘"
    echo

    ask() {
        local key="$1" label="$2" secret="${3:-no}" default="${4:-}"
        local input
        if [[ "$secret" == "yes" ]]; then
            read -rsp "  ${label}: " input; echo
        else
            if [[ -n "$default" ]]; then
                read -rp "  ${label} [${default}]: " input
                input="${input:-$default}"
            else
                read -rp "  ${label}: " input
            fi
        fi
        [[ -n "$input" ]] && set_var "$key" "$input"
    }

    echo "  ─── Telegram ───"
    ask BOT_TOKEN        "Токен бота от @BotFather" yes
    ask BOT_USERNAME     "Имя бота без @"
    ask ADMIN_TELEGRAM_ID "Ваш Telegram ID (от @userinfobot)"

    echo
    echo "  ─── Админ-панель ───"
    ask ADMIN_EMAIL     "Email администратора" no "admin@example.com"
    ask ADMIN_PASSWORD  "Пароль админа (мин. 12 симв.)" yes

    echo
    echo "  ─── Remnawave API ───"
    ask REMNAWAVE_URL   "URL панели (https://panel.example.com)"
    ask REMNAWAVE_TOKEN "API-токен Remnawave" yes

    chmod 600 .env
    ok ".env настроен"
fi

# ============================================================
# 5. АВТООТКРЫТИЕ ВСЕХ ПОРТОВ
# ============================================================
step "5/8. ОТКРЫТИЕ ВСЕХ ПОРТОВ"

# Собираем порты из docker-compose.yml
log "Анализ портов в docker-compose.yml..."

PORTS=("${DEFAULT_PORTS[@]}")

if [[ -f docker-compose.yml ]]; then
    # Ищем строки вида "8000:8000" или "- 3000:3000" или "published: 8443"
    while IFS= read -r line; do
        # Формат "X:Y" → берём X (внешний порт)
        port=$(echo "$line" | grep -oE '"?[0-9]+:[0-9]+"?' | cut -d: -f1 | tr -d '"')
        if [[ -n "$port" ]] && [[ "$port" =~ ^[0-9]+$ ]]; then
            PORTS+=("$port")
        fi
    done < <(grep -E '^\s*-\s*"?[0-9]+:[0-9]+' docker-compose.yml 2>/dev/null || true)

    # Ищем "published: XXXX" (long syntax)
    while IFS= read -r port; do
        [[ "$port" =~ ^[0-9]+$ ]] && PORTS+=("$port")
    done < <(grep -E 'published:\s*"?[0-9]+' docker-compose.yml 2>/dev/null | grep -oE '[0-9]+' || true)
fi

# Убираем дубли
UNIQUE_PORTS=($(printf '%s\n' "${PORTS[@]}" | sort -nu))

log "Найдено портов: ${UNIQUE_PORTS[*]}"

# Настраиваем UFW
if command -v ufw >/dev/null 2>&1; then
    # Сброс политик по умолчанию (только для вход. трафика)
    ufw --force reset >/dev/null 2>&1 || true
    ufw default deny incoming  >/dev/null 2>&1
    ufw default allow outgoing >/dev/null 2>&1

    for port in "${UNIQUE_PORTS[@]}"; do
        ufw allow "$port"/tcp >/dev/null 2>&1 || true
        ufw allow "$port"/udp >/dev/null 2>&1 || true
    done

    # Docker-friendly: разрешаем весь трафик от docker-сети
    if [[ -d /etc/docker ]]; then
        # Опционально: разрешить весь трафик от docker0
        true
    fi

    ufw --force enable >/dev/null 2>&1
    ok "UFW: открыто ${#UNIQUE_PORTS[@]} портов"
    log "Проверить: ufw status numbered"
else
    warn "UFW не найден — порты открываются через iptables напрямую"
fi

# Дополнительно — iptables (на случай, если UFW конфликтует с Docker)
if command -v iptables >/dev/null 2>&1; then
    for port in "${UNIQUE_PORTS[@]}"; do
        iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null || \
            iptables -I INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null || true
    done
    ok "iptables: правила добавлены"
fi

# ============================================================
# 6. ЗАПУСК КОНТЕЙНЕРОВ
# ============================================================
step "6/8. СБОРКА И ЗАПУСК"

log "Скачивание образов и сборка (3–7 минут)..."
docker compose pull 2>/dev/null || true
docker compose up -d --build

log "Ожидание запуска сервисов (40 секунд)..."
sleep 40

# ============================================================
# 7. ПРОВЕРКА ЗДОРОВЬЯ
# ============================================================
step "7/8. ПРОВЕРКА ЗДОРОВЬЯ СЕРВИСОВ"

docker compose ps

RUNNING=$(docker compose ps --status running --quiet 2>/dev/null | wc -l)
TOTAL=$(docker compose ps --quiet 2>/dev/null | wc -l)

echo
if [[ "$RUNNING" -eq "$TOTAL" && "$TOTAL" -gt 0 ]]; then
    ok "Все сервисы работают ($RUNNING/$TOTAL)"
else
    warn "Работают $RUNNING из $TOTAL сервисов"
    echo
    log "Последние 100 строк логов:"
    docker compose logs --tail=100
fi

# ============================================================
# 8. ИТОГ
# ============================================================
step "8/8. ГОТОВО"

SERVER_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "ВАШ_IP")

echo "═══════════════════════════════════════════════════════════"
echo -e "  ${GREEN}${BOLD}✅ УСТАНОВКА ЗАВЕРШЕНА${NC}"
echo "═══════════════════════════════════════════════════════════"
echo
echo "  📁 Проект    : $PROJECT_DIR"
echo "  🌐 IP         : $SERVER_IP"
echo "  🔓 Открыто    : ${UNIQUE_PORTS[*]}"
echo
echo "  🔧 Управление:"
echo "     cd $PROJECT_DIR"
echo "     docker compose ps             # статус"
echo "     docker compose logs -f        # логи"
echo "     docker compose restart        # перезапуск"
echo "     docker compose down           # остановить"
echo "     docker compose up -d --build  # обновить"
echo
echo "  🔄 Обновление:"
echo "     cd $PROJECT_DIR && git pull && docker compose up -d --build"
echo
echo "  📱 Проверка:"
echo "     1. Напишите боту /start в Telegram"
echo "     2. Откройте http://$SERVER_IP в браузере"
echo
echo "  🔥 Порты:"
echo "     ufw status numbered"
echo
echo "═══════════════════════════════════════════════════════════"
