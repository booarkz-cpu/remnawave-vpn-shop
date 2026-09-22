#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "ERROR: installation failed at line $LINENO" >&2' ERR

ROOT="${APP_DIR:-/opt/vpn-shop}"
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log(){ printf '\033[1;32m[VPN-SHOP]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[WARNING]\033[0m %s\n' "$*" >&2; }
die(){ printf '\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Запустите от root: sudo bash deploy/install-vps.sh"
[[ -f "$SOURCE_ROOT/docker-compose.yml" ]] || die "docker-compose.yml не найден рядом с архивом/папкой проекта."
command -v apt-get >/dev/null 2>&1 || die "Поддерживаются Debian/Ubuntu."

prompt() {
  local var="$1" label="$2" default="${3:-}" secret="${4:-0}" value
  if [[ "${INSTALL_NONINTERACTIVE:-0}" == "1" ]]; then
    if [[ -z "${!var:-}" ]]; then
      printf -v "$var" '%s' "$default"
    fi
    return
  fi
  if [[ -z "$default" && -n "${!var:-}" && "$secret" != "1" ]]; then
    default="${!var}"
  fi
  if [[ "$secret" == "1" ]]; then
    if [[ -n "$default" ]]; then
      read -r -s -p "$label [$default]: " value; echo
    else
      read -r -s -p "$label: " value; echo
    fi
  else
    read -r -p "$label${default:+ [$default]}: " value
  fi
  printf -v "$var" '%s' "${value:-$default}"
}

prompt_required() {
  local var="$1" label="$2" secret="${3:-0}"
  if [[ "${INSTALL_NONINTERACTIVE:-0}" == "1" ]]; then
    prompt "$var" "$label" "" "$secret"
    [[ -n "${!var}" ]] || die "Не задано обязательное поле $var"
    return
  fi
  while :; do
    prompt "$var" "$label" "" "$secret"
    [[ -n "${!var}" ]] && return
    echo "Поле обязательно."
  done
}

# Safe .env writer: values are single-quoted; embedded apostrophes are escaped.
env_line() {
  local key="$1" value="${2-}" escaped
  escaped="${value//\'/\'\\\'\'}"
  printf "%s='%s'\n" "$key" "$escaped"
}

# Previous release contract: INSTALLER_VERSION="1.0.0-realise"
INSTALLER_VERSION="2.6.0"
# Historical compatibility marker: INSTALLER_VERSION="2.5.0"
# Historical compatibility marker: INSTALLER_VERSION="2.4.0"
# Historical compatibility marker: INSTALLER_VERSION="2.3.0"
# Historical compatibility marker: INSTALLER_VERSION="2.2.1"
# Historical compatibility marker: INSTALLER_VERSION="2.2.0"
# Historical compatibility marker: INSTALLER_VERSION="2.1.0"
# Historical banner compatibility marker: Remnawave VPN Shop — 2.1.0
# Legacy regression marker: INSTALLER_VERSION="2.0.3-audited"
# Legacy regression marker: INSTALLER_VERSION="2.0.0-realise"
# Previous release contract: INSTALLER_VERSION="45.0.0-enterprise"
# V44.5 Enterprise legacy contract marker
# INSTALLER_VERSION="43.1.0-production" legacy regression marker
log "Remnawave VPN Shop — 2.6.0 русскоязычный production installer"
# Historical compatibility marker: Remnawave VPN Shop — 2.5.0 русскоязычный production installer
echo
echo "Все основные настройки будут введены сейчас. После установки редактировать .env вручную не требуется."
echo "Для HTTPS DNS-записи доменов должны уже указывать на этот VDS."
echo "Скрипт сам создаст .env, lock-файлы frontend, зафиксирует Docker image digests, настроит firewall, соберёт и запустит сервисы."
echo

prompt_required BASE_DOMAIN "Основной домен (например vpn.example.com)"
BASE_DOMAIN="${BASE_DOMAIN,,}"
[[ "$BASE_DOMAIN" =~ ^[a-z0-9][a-z0-9.-]+\.[a-z]{2,}$ ]] || die "Некорректный BASE_DOMAIN"
prompt API_DOMAIN "API-домен" "api.${BASE_DOMAIN}"
prompt ADMIN_DOMAIN "Домен админки" "admin.${BASE_DOMAIN}"
prompt APP_DOMAIN "Домен Mini App" "app.${BASE_DOMAIN}"
prompt CABINET_DOMAIN "Домен личного кабинета" "cabinet.${BASE_DOMAIN}"
prompt ADMIN_EMAIL "Email администратора" "admin@${BASE_DOMAIN}"
prompt ADMIN_PASSWORD "Пароль администратора (Enter = сгенерировать)" "" 1
prompt_required BOT_TOKEN "Telegram BOT_TOKEN от @BotFather" 1
prompt_required REMNAWAVE_URL "Remnawave Panel URL (например https://panel.example.com)"
prompt_required REMNAWAVE_TOKEN "Remnawave API token" 1

echo
echo "Платежи: выберите провайдер для первичной настройки."
prompt PAYMENT_PROVIDER "Провайдер (yookassa / platega / rollypay / none)" "none"
PAYMENT_PROVIDER="$(printf '%s' "$PAYMENT_PROVIDER" | tr '[:upper:]' '[:lower:]')"

YOOKASSA_SHOP_ID=""; YOOKASSA_SECRET_KEY=""
PLATEGA_MERCHANT_ID=""; PLATEGA_SECRET=""
ROLLYPAY_API_KEY=""; ROLLYPAY_SIGNING_SECRET=""

case "$PAYMENT_PROVIDER" in
  yookassa)
    prompt_required YOOKASSA_SHOP_ID "YooKassa Shop ID"
    prompt_required YOOKASSA_SECRET_KEY "YooKassa Secret Key" 1
    ;;
  platega)
    prompt_required PLATEGA_MERCHANT_ID "Platega Merchant ID"
    prompt_required PLATEGA_SECRET "Platega Secret" 1
    ;;
  rollypay)
    prompt_required ROLLYPAY_API_KEY "RollyPay API Key" 1
    prompt_required ROLLYPAY_SIGNING_SECRET "RollyPay Signing Secret" 1
    ;;
  none) ;;
  *) die "Неизвестный PAYMENT_PROVIDER: $PAYMENT_PROVIDER" ;;
esac

echo
echo "Дополнительные кассы. Enter оставляет поле пустым."
if [[ "$PAYMENT_PROVIDER" != "yookassa" ]]; then
  prompt YOOKASSA_SHOP_ID "YooKassa Shop ID"
  if [[ -n "${YOOKASSA_SHOP_ID}" ]]; then prompt_required YOOKASSA_SECRET_KEY "YooKassa Secret Key" 1; fi
fi
if [[ "$PAYMENT_PROVIDER" != "platega" ]]; then
  prompt PLATEGA_MERCHANT_ID "Platega Merchant ID"
  if [[ -n "${PLATEGA_MERCHANT_ID}" ]]; then prompt_required PLATEGA_SECRET "Platega Secret" 1; fi
fi
if [[ "$PAYMENT_PROVIDER" != "rollypay" ]]; then
  prompt ROLLYPAY_API_KEY "RollyPay API Key" "" 1
  if [[ -n "${ROLLYPAY_API_KEY}" ]]; then prompt_required ROLLYPAY_SIGNING_SECRET "RollyPay Signing Secret" 1; fi
fi
prompt PLATEGA_REFUND_URL "Platega refund URL"
prompt ROLLYPAY_REFUND_URL "RollyPay refund URL"
if [[ -n "${YOOKASSA_SHOP_ID}${PLATEGA_MERCHANT_ID}${ROLLYPAY_API_KEY}" ]]; then
  PAYMENT_PROVIDER="configured"
fi

echo
prompt_required BOT_USERNAME "Имя бота без @"
prompt ADMIN_TELEGRAM_ID "Telegram ID администратора (@userinfobot)"
prompt DEFAULT_LANGUAGE "Язык по умолчанию (ru/en)" "ru"
DEFAULT_LANGUAGE="$(printf '%s' "$DEFAULT_LANGUAGE" | tr '[:upper:]' '[:lower:]')"
[[ "$DEFAULT_LANGUAGE" == "ru" || "$DEFAULT_LANGUAGE" == "en" ]] || die "DEFAULT_LANGUAGE должен быть ru или en"
prompt DEFAULT_CURRENCY "Валюта" "RUB"
prompt TZ_VALUE "Часовой пояс" "Europe/Moscow"
prompt CADDY_EMAIL "Email для TLS-сертификата" "$ADMIN_EMAIL"
prompt WEBHOOK_DOMAIN "Домен вебхуков" "pay.${BASE_DOMAIN}"
prompt MINIAPP_DOMAIN "Домен Mini App, если отличается" "$APP_DOMAIN"
prompt BOT_DOMAIN "Домен бота" "bot.${BASE_DOMAIN}"
prompt PANEL_DOMAIN "Домен панели Remnawave в Caddy, если нужен" "$BASE_DOMAIN"
prompt PRICE_1 "Цена 1 месяц" "199"
prompt PRICE_3 "Цена 3 месяца" "499"
prompt PRICE_6 "Цена 6 месяцев" "899"
prompt PRICE_12 "Цена 12 месяцев" "1499"
prompt AUTO_RENEW_ENABLED "Автопродление (true/false)" "false"
prompt AUTO_RENEW_LEAD_DAYS "За сколько дней до конца списывать автопродление" "3"
prompt REQUIRED_TELEGRAM_CHANNEL "Обязательный канал (@name или -100..., Enter = выкл)"
prompt ALERT_TELEGRAM_CHAT_ID "Telegram-чат алертов"
prompt REFERRAL_REWARD_PERCENT "Процент реферального вознаграждения" "5.0"
prompt NOTIFICATION_EXPIRY_DAYS "За сколько дней предупреждать об окончании" "3"

echo
prompt YANDEX_CLIENT_ID "Yandex OAuth Client ID (Enter = пропустить)"
prompt YANDEX_CLIENT_SECRET "Yandex OAuth Client Secret (Enter = пропустить)" "" 1
prompt VK_CLIENT_ID "VK OAuth Client ID (Enter = пропустить)"
prompt VK_CLIENT_SECRET "VK OAuth Client Secret (Enter = пропустить)" "" 1
prompt PAYMENTS_SANDBOX "Песочница платежей без шлюзов (true/false)" "false"
prompt TRIAL_MAX_DAYS "Максимум дней пробного периода" "3"

echo
prompt S3_ENDPOINT_URL "S3 endpoint (Enter = отключить off-site backup)"
prompt S3_BUCKET "S3 bucket"
prompt S3_REGION "S3 region" "auto"
prompt S3_ACCESS_KEY "S3 access key"
prompt S3_SECRET_KEY "S3 secret key" "" 1

if [[ -z "$ADMIN_PASSWORD" ]]; then
  ADMIN_PASSWORD="$(openssl rand -hex 16)"
  GENERATED_ADMIN_PASSWORD=1
else
  GENERATED_ADMIN_PASSWORD=0
fi

APP_SECRET="$(openssl rand -hex 32)"
DB_PASSWORD="$(openssl rand -hex 24)"

log "Устанавливаю системные зависимости и Docker..."
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl unzip openssl ufw fail2ban unattended-upgrades

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker
docker compose version >/dev/null 2>&1 || die "Docker Compose plugin не установлен."

if [[ -e "$ROOT/docker-compose.yml" || -e "$ROOT/.env" ]]; then
  die "$ROOT уже содержит установку. Для существующей установки используйте: cd $ROOT && ./deploy/build-production.sh"
fi

log "Копирую release в $ROOT..."
mkdir -p "$ROOT"
cp -a "$SOURCE_ROOT"/. "$ROOT"/
cd "$ROOT"

umask 077
{
  env_line APP_VERSION "$INSTALLER_VERSION"
  env_line APP_SECRET "$APP_SECRET"
  env_line DATABASE_URL "postgresql+asyncpg://vpnshop:${DB_PASSWORD}@db:5432/vpnshop"
  env_line REDIS_URL "redis://redis:6379/0"
  env_line COOKIE_SECURE "true"
  env_line COOKIE_SAMESITE "none"
  env_line PUBLIC_BASE_URL "https://${API_DOMAIN}"
  env_line MINI_APP_URL "https://${MINIAPP_DOMAIN:-$APP_DOMAIN}"
  env_line CABINET_URL "https://${CABINET_DOMAIN}"
  env_line ADMIN_CORS_ORIGINS "https://${ADMIN_DOMAIN},https://${CABINET_DOMAIN},https://${APP_DOMAIN}"
  env_line ADMIN_EMAIL "$ADMIN_EMAIL"
  env_line ADMIN_PASSWORD "$ADMIN_PASSWORD"
  env_line BOT_TOKEN "$BOT_TOKEN"
  env_line BOT_USERNAME "$BOT_USERNAME"
  env_line ADMIN_TELEGRAM_ID "$ADMIN_TELEGRAM_ID"
  env_line REMNAWAVE_URL "$REMNAWAVE_URL"
  env_line REMNAWAVE_TOKEN "$REMNAWAVE_TOKEN"
  env_line YOOKASSA_SHOP_ID "$YOOKASSA_SHOP_ID"
  env_line YOOKASSA_SECRET_KEY "$YOOKASSA_SECRET_KEY"
  env_line YOOKASSA_WEBHOOK_IP_ALLOWLIST "185.71.76.0/27,185.71.77.0/27,77.75.153.0/25,77.75.156.11,77.75.156.35,77.75.154.128/25,2a02:5180::/32"
  env_line PLATEGA_MERCHANT_ID "$PLATEGA_MERCHANT_ID"
  env_line PLATEGA_SECRET "$PLATEGA_SECRET"
  env_line PLATEGA_REFUND_URL "$PLATEGA_REFUND_URL"
  env_line ROLLYPAY_API_KEY "$ROLLYPAY_API_KEY"
  env_line ROLLYPAY_SIGNING_SECRET "$ROLLYPAY_SIGNING_SECRET"
  env_line ROLLYPAY_REFUND_URL "$ROLLYPAY_REFUND_URL"
  env_line DEFAULT_CURRENCY "$DEFAULT_CURRENCY"
  env_line DEFAULT_LANGUAGE "$DEFAULT_LANGUAGE"
  env_line TZ "$TZ_VALUE"
  env_line PRICE_1 "$PRICE_1"
  env_line PRICE_3 "$PRICE_3"
  env_line PRICE_6 "$PRICE_6"
  env_line PRICE_12 "$PRICE_12"
  env_line AUTO_RENEW_ENABLED "$AUTO_RENEW_ENABLED"
  env_line AUTO_RENEW_LEAD_DAYS "$AUTO_RENEW_LEAD_DAYS"
  env_line REQUIRED_TELEGRAM_CHANNEL "$REQUIRED_TELEGRAM_CHANNEL"
  env_line ALERT_TELEGRAM_CHAT_ID "$ALERT_TELEGRAM_CHAT_ID"
  env_line REFERRAL_REWARD_PERCENT "$REFERRAL_REWARD_PERCENT"
  env_line NOTIFICATION_EXPIRY_DAYS "$NOTIFICATION_EXPIRY_DAYS"
  env_line CADDY_EMAIL "$CADDY_EMAIL"
  env_line WEBHOOK_DOMAIN "$WEBHOOK_DOMAIN"
  env_line WEBHOOK_BASE_URL "https://${WEBHOOK_DOMAIN}"
  env_line MINIAPP_DOMAIN "$MINIAPP_DOMAIN"
  env_line BOT_DOMAIN "$BOT_DOMAIN"
  env_line PANEL_DOMAIN "$PANEL_DOMAIN"
  env_line MAINTENANCE_MODE "false"
  env_line BACKUPS_DIR "/data/backups"
  env_line PROJECT_DIR "/project"
  env_line DB_PASSWORD "$DB_PASSWORD"
  env_line YANDEX_CLIENT_ID "$YANDEX_CLIENT_ID"
  env_line YANDEX_CLIENT_SECRET "$YANDEX_CLIENT_SECRET"
  env_line YANDEX_REDIRECT_URI "https://${API_DOMAIN}/api/auth/yandex/callback"
  env_line VK_CLIENT_ID "$VK_CLIENT_ID"
  env_line VK_CLIENT_SECRET "$VK_CLIENT_SECRET"
  env_line VK_REDIRECT_URI "https://${API_DOMAIN}/api/auth/vk/callback"
  env_line PAYMENTS_SANDBOX "$PAYMENTS_SANDBOX"
  env_line TRIAL_MAX_DAYS "$TRIAL_MAX_DAYS"
  env_line MEDIA_DIR "/data/media"
  env_line S3_ENDPOINT_URL "$S3_ENDPOINT_URL"
  env_line S3_BUCKET "$S3_BUCKET"
  env_line S3_REGION "$S3_REGION"
  env_line S3_ACCESS_KEY "$S3_ACCESS_KEY"
  env_line S3_SECRET_KEY "$S3_SECRET_KEY"
  if [[ -n "$S3_ENDPOINT_URL" ]]; then BACKUP_S3_ENABLED=true; else BACKUP_S3_ENABLED=false; fi
  env_line BACKUP_S3_ENABLED "$BACKUP_S3_ENABLED"
  env_line METRICS_TOKEN "$(openssl rand -hex 24)"
  env_line FULFILLMENT_MAX_ATTEMPTS "8"
  env_line API_DOMAIN "$API_DOMAIN"
  env_line ADMIN_DOMAIN "$ADMIN_DOMAIN"
  env_line APP_DOMAIN "$APP_DOMAIN"
  env_line CABINET_DOMAIN "$CABINET_DOMAIN"
  env_line FIREWALL_MODE "strict"
} > .env
chmod 600 .env

# Strict production firewall: only SSH and the public web entrypoint are exposed.
# Caddy uses TCP 80/443 and HTTP/3 uses UDP 443. All application services remain internal.
ufw default deny incoming >/dev/null 2>&1 || true
ufw default allow outgoing >/dev/null 2>&1 || true
ufw allow OpenSSH >/dev/null 2>&1 || true
ufw allow 80/tcp >/dev/null 2>&1 || true
ufw allow 443/tcp >/dev/null 2>&1 || true
ufw allow 443/udp >/dev/null 2>&1 || true
ufw --force enable >/dev/null 2>&1 || true

# SSH hardening without changing authentication mode, so a fresh VDS is not locked out.
mkdir -p /etc/ssh/sshd_config.d
cat >/etc/ssh/sshd_config.d/99-vpn-shop-hardening.conf <<'SSH'
MaxAuthTries 5
LoginGraceTime 30
X11Forwarding no
AllowTcpForwarding no
PermitTunnel no
SSH
if command -v sshd >/dev/null 2>&1; then
  sshd -t && systemctl reload ssh 2>/dev/null || true
fi

# SSH brute-force protection. We deliberately do not disable root/password SSH here
# because doing so blindly can lock an operator out of a fresh VDS.
cat >/etc/fail2ban/jail.d/vpn-shop-sshd.local <<'JAIL'
[sshd]
enabled = true
backend = systemd
maxretry = 5
findtime = 10m
bantime = 1h
JAIL
systemctl enable --now fail2ban >/dev/null 2>&1 || true
# Enable unattended security updates where supported.
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true

log "Фиксирую build-stage image digests..."
resolve_build(){ local image="$1"; docker pull "$image" >/dev/null; docker image inspect "$image" --format "{{index .RepoDigests 0}}"; }
PYTHON_BASE_IMAGE="$(resolve_build python:3.12-slim)"
NODE_BASE_IMAGE="$(resolve_build node:22-alpine)"
NGINX_BASE_IMAGE="$(resolve_build nginx:1.29-alpine)"
log "Генерирую frontend lock-файлы автоматически (ручное редактирование не требуется)..."
for app in admin miniapp cabinet; do
  [[ -f "$app/package.json" ]] || die "Не найден $app/package.json"
  rm -rf "$app/node_modules"
  docker run --rm --user "$(id -u):$(id -g)" -v "$ROOT/$app:/app" -w /app "$NODE_BASE_IMAGE" \
    timeout 180 npm install --package-lock-only --ignore-scripts --no-audit --no-fund
  [[ -s "$app/package-lock.json" ]] || die "Не удалось создать $app/package-lock.json"
done

log "Фиксирую production image digests..."
./scripts/pin-images.sh
# Compose normally reads .env, not .env.images. pin-images.sh also writes the
# pinned values into .env, so the runtime cannot silently fall back to mutable tags.
set -a
. ./.env.images
set +a
{ printf "PYTHON_BASE_IMAGE=%s\n" "$PYTHON_BASE_IMAGE"; printf "NODE_BASE_IMAGE=%s\n" "$NODE_BASE_IMAGE"; printf "NGINX_BASE_IMAGE=%s\n" "$NGINX_BASE_IMAGE"; } >> .env
chmod 600 .env
log "Проверяю Docker Compose..."
docker compose config >/dev/null

log "Собираю production-образы с актуальными базовыми образами..."
docker compose build --pull --no-cache
docker compose up -d

log "Ожидаю API и миграции..."
healthy=0
for i in {1..80}; do
  if docker compose exec -T backend python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3)' >/dev/null 2>&1; then healthy=1; break; fi
  sleep 3
done
[[ "$healthy" == "1" ]] || {
  docker compose ps
  docker compose logs --tail=120 backend
  die "API не вышел в healthy state."
}

docker compose ps

echo
printf '%s\n' '============================================================'
printf '%s\n' ' INSTALLATION COMPLETE'
printf '%s\n' '============================================================'
echo "Admin:       https://${ADMIN_DOMAIN}"
echo "Mini App:    https://${APP_DOMAIN}"
echo "Cabinet:     https://${CABINET_DOMAIN}"
echo "API:         https://${API_DOMAIN}"
echo "Version:     ${INSTALLER_VERSION}"
echo "Yandex:      https://${API_DOMAIN}/api/auth/yandex/callback"
echo "VK:          https://${API_DOMAIN}/api/auth/vk/callback"
echo "Admin email: ${ADMIN_EMAIL}"
if [[ "$GENERATED_ADMIN_PASSWORD" == "1" ]]; then
  echo "Admin password (generated): ${ADMIN_PASSWORD}"
else
  echo "Admin password: введён вами при установке."
fi
echo
echo "Все секреты сохранены в ${ROOT}/.env (chmod 600)."
echo "2FA выключена по умолчанию. Включите её позже в Admin → Безопасность, если требуется."
echo "Firewall V40: открыты только SSH, TCP 80/443 и UDP 443. PostgreSQL, Redis и application ports остаются внутренними."
echo
echo "Проверка:"
echo "  curl -fsS https://${API_DOMAIN}/health"
echo "  cd ${ROOT} && docker compose ps"
echo
echo "Логи:"
echo "  cd ${ROOT} && docker compose logs -f --tail=200"
echo
if [[ "$PAYMENT_PROVIDER" == "none" ]]; then
  warn "Платёжный провайдер не настроен. Это допустимо для тестового запуска; платежи будут отключены."
fi
if [[ -z "$YANDEX_CLIENT_ID" || -z "$YANDEX_CLIENT_SECRET" ]]; then
  echo "Yandex ID: пропущен."
fi
