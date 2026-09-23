#!/usr/bin/env bash
#
# Remnawave VPN Shop — one-step installer / установка в один шаг
#
#   curl -fsSL https://raw.githubusercontent.com/booarkz-cpu/remnawave-vpn-shop/main/install.sh | sudo bash
#
# Этот файл готовит Docker и исходники, затем передаёт управление
# deploy/install-vps.sh. Все операторские данные вводятся там.
# Внутренние порты PostgreSQL, Redis, API и панелей наружу не открываются.
#
# This wrapper prepares Docker and the source tree, then execs
# deploy/install-vps.sh, which asks for every operator setting.
# PostgreSQL, Redis, the API and the panels stay off the public firewall.
#
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/booarkz-cpu/remnawave-vpn-shop.git}"
BRANCH="${BRANCH:-main}"
SOURCE_DIR="${SOURCE_DIR:-/opt/vpn-shop-src}"

if [[ $EUID -ne 0 ]]; then
  echo "Запускать от root: sudo bash install.sh" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
if [[ -f /etc/os-release ]]; then
  . /etc/os-release
  if [[ "${ID:-}" != "ubuntu" && "${ID:-}" != "debian" ]]; then
    echo "Тестировалось на Ubuntu/Debian. Ваша ОС: ${ID:-unknown}" >&2
  fi
fi

apt-get update -y
apt-get install -y ca-certificates curl git openssl
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker
docker compose version >/dev/null 2>&1 || { echo "Docker Compose plugin не установлен." >&2; exit 1; }

SCRIPT_DIR=""
if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/docker-compose.yml" && -f "$SCRIPT_DIR/deploy/install-vps.sh" ]]; then
  SOURCE_DIR="$SCRIPT_DIR"
else
  mkdir -p "$SOURCE_DIR"
  if [[ -d "$SOURCE_DIR/.git" ]]; then
    git -C "$SOURCE_DIR" pull --ff-only origin "$BRANCH"
  else
    rm -rf "$SOURCE_DIR"
    git clone --branch "$BRANCH" "$REPO_URL" "$SOURCE_DIR"
  fi
fi

if [[ ! -f "$SOURCE_DIR/deploy/install-vps.sh" ]]; then
  echo "Не найден deploy/install-vps.sh в $SOURCE_DIR" >&2
  exit 1
fi

if [[ ! -t 0 && "${INSTALL_NONINTERACTIVE:-0}" != "1" ]]; then
  if [[ ! -r /dev/tty ]]; then
    echo "Нет терминала для вопросов установщика. Запустите bash install.sh из SSH или задайте INSTALL_NONINTERACTIVE=1." >&2
    exit 1
  fi
  exec bash "$SOURCE_DIR/deploy/install-vps.sh" </dev/tty
fi
exec bash "$SOURCE_DIR/deploy/install-vps.sh"
