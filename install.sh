cat > install.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[FAIL]${NC} $*" >&2; }

[[ $EUID -ne 0 ]] && { err "Запускать от root: sudo $0"; exit 1; }

if [[ -f /etc/os-release ]]; then
  . /etc/os-release
  [[ "$ID" != "ubuntu" && "$ID" != "debian" ]] && warn "Тестировалось на Ubuntu/Debian. Ваша ОС: $ID"
fi

PROJECT_DIR="${PROJECT_DIR:-/opt/remnawave-shop}"
GIT_REPO="${GIT_REPO:-https://github.com/booarkz-cpu/remnawave-vpn-shop.git}"
SETUP_NGINX="${SETUP_NGINX:-ask}"

log "Обновление системы..."
export DEBIAN_FRONTEND=noninteractive
apt update -y && apt upgrade -y
apt install -y curl wget unzip git ufw ca-certificates gnupg lsb-release openssl jq nano
ok "Базовые пакеты установлены."

if ! command -v docker >/dev/null 2>&1; then
  log "Установка Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
  ok "Docker: $(docker --version)"
else
  ok "Docker уже установлен"
fi

if ! docker compose version >/dev/null 2>&1; then
  apt install -y docker-compose-plugin
fi
ok "Docker Compose: $(docker compose version)"

log "Подготовка проекта в $PROJECT_DIR"
if [[ -d "$PROJECT_DIR/.git" ]]; then
  cd "$PROJECT_DIR" && git pull --ff-only || warn "git pull не удался"
else
  mkdir -p "$PROJECT_DIR" && cd "$PROJECT_DIR"
  git clone "$GIT_REPO" .
fi

if [[ ! -f docker-compose.yml ]]; then
  FOUND=$(find "$PROJECT_DIR" -maxdepth 3 -name "docker-compose.yml" -print -quit)
  [[ -n "$FOUND" ]] && PROJECT_DIR=$(dirname "$FOUND") && cd "$PROJECT_DIR" || { err "docker-compose.yml не найден"; exit 1; }
fi
ok "Проект в $PROJECT_DIR"

if [[ -f .env ]]; then
  ok ".env уже существует"
else
  [[ ! -f .env.example ]] && { err ".env.example не найден"; exit 1; }
  cp .env.example .env

  prompt_var() {
    local key="$1" desc="$2" secret="${3:-no}" current input
    current=$(grep -E "^${key}=" .env | head -n1 | cut -d= -f2- || true)
    if [[ "$secret" == "yes" ]]; then
      read -rsp "  ${key} (${desc}) [${current}]: " input; echo
    else
      read -rp  "  ${key} (${desc}) [${current}]: " input
    fi
    [[ -z "$input" ]] && input="$current"
    [[ -z "$input" ]] && return 0
    local tmp; tmp=$(mktemp)
    awk -v k="$key" -v v="$input" 'BEGIN{FS=OFS="="} $1==k{$0=k"="v} {print}' .env > "$tmp" && mv "$tmp" .env
  }

  prompt_var "APP_SECRET"      "секретный ключ приложения"
  prompt_var "BOT_TOKEN"       "токен бота от @BotFather" yes
  prompt_var "ADMIN_EMAIL"     "email администратора"
  prompt_var "ADMIN_PASSWORD"  "пароль администратора" yes
  prompt_var "REMNAWAVE_URL"   "URL панели Remnawave"
  prompt_var "REMNAWAVE_TOKEN" "токен API Remnawave" yes

  grep -qE "^APP_SECRET=$|^APP_SECRET=change" .env && sed -i "s|^APP_SECRET=.*|APP_SECRET=$(openssl rand -hex 32)|" .env && ok "APP_SECRET сгенерирован"
  grep -qE "^DB_PASSWORD=$|^DB_PASSWORD=change" .env && sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -hex 16)|" .env && ok "Пароль БД сгенерирован"
  chmod 600 .env
  ok ".env настроен"
fi

log "Сборка и запуск контейнеров..."
docker compose pull || true
docker compose up -d --build
sleep 20

docker compose ps

if docker compose ps --status running | grep -q "running"; then
  ok "Сервисы запущены"
else
  warn "Не все сервисы запустились. Логи:"
  docker compose logs --tail=80
fi

if command -v ufw >/dev/null 2>&1; then
  ufw allow 22/tcp || true
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
  ufw --force enable || true
  ok "UFW настроен"
fi

if [[ "$SETUP_NGINX" == "ask" ]]; then
  read -rp "Настроить Nginx + SSL? (y/N): " ANS
  [[ "${ANS,,}" == "y" ]] && SETUP_NGINX="yes" || SETUP_NGINX="no"
fi

if [[ "$SETUP_NGINX" == "yes" ]]; then
  read -rp "Домен (например shop.example.com): " DOMAIN
  read -rp "Порт backend (Enter=8000): " BACKEND_PORT
  BACKEND_PORT="${BACKEND_PORT:-8000}"
  apt install -y nginx certbot python3-certbot-nginx
  cat > "/etc/nginx/sites-available/${DOMAIN}" <<NGINX
server {
    listen 80;
    server_name ${DOMAIN};
    location / {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
NGINX
  ln -sf "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"
  nginx -t && systemctl reload nginx
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email || warn "Certbot: проверьте DNS"
  ok "Nginx + SSL настроены"
fi

echo
echo "====================================================="
ok "Установка завершена"
echo " Проект : $PROJECT_DIR"
echo " Логи   : docker compose logs -f"
echo " Стоп   : docker compose down"
echo "====================================================="
EOF
chmod +x install.sh && \
git add install.sh && \
git commit -m "Update install.sh" && \
git push origin main && \
echo "✅ install.sh обновлён и запушен"
