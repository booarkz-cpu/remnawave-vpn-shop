#!/usr/bin/env bash
set -Eeuo pipefail
APP_DIR="${APP_DIR:-/opt/vpn-shop}"
cd "$APP_DIR"
command -v docker >/dev/null || { echo "Docker is required" >&2; exit 2; }

resolve(){
  local image="$1"
  docker pull "$image" >/dev/null
  docker image inspect "$image" --format '{{index .RepoDigests 0}}'
}
REDIS_IMAGE="$(resolve redis:7.4-alpine)"
POSTGRES_IMAGE="$(resolve postgres:16-alpine)"
CADDY_IMAGE="$(resolve caddy:2.10-alpine)"
{
  echo "REDIS_IMAGE=$REDIS_IMAGE"
  echo "POSTGRES_IMAGE=$POSTGRES_IMAGE"
  echo "CADDY_IMAGE=$CADDY_IMAGE"
} > .env.images
chmod 0600 .env.images

# Docker Compose reads .env automatically. Keep the immutable digests there too,
# otherwise a plain `docker compose up` could silently fall back to mutable tags.
if [[ -f .env ]]; then
  tmp=".env.tmp.$$"
  awk '!/^(REDIS_IMAGE|POSTGRES_IMAGE|CADDY_IMAGE)=/' .env > "$tmp"
  cat .env.images >> "$tmp"
  chmod 0600 "$tmp"
  mv "$tmp" .env
fi
printf 'Pinned images written to %s/.env.images and .env\n' "$APP_DIR"
