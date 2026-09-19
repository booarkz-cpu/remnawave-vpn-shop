#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ -f .env.images ]]; then set -a; . ./.env.images; set +a; fi
python3 -m pytest -q
python3 -m compileall -q backend
if command -v docker >/dev/null 2>&1; then if [[ "${REQUIRE_PINNED_IMAGES:-1}" == "1" ]]; then
  [[ -f .env.images ]] || { echo "Missing .env.images: run ./scripts/pin-images.sh before production start." >&2; exit 2; }
  grep -Eq '^REDIS_IMAGE=.*@sha256:' .env.images || { echo "REDIS_IMAGE is not digest-pinned" >&2; exit 2; }
  grep -Eq '^POSTGRES_IMAGE=.*@sha256:' .env.images || { echo "POSTGRES_IMAGE is not digest-pinned" >&2; exit 2; }
  grep -Eq '^CADDY_IMAGE=.*@sha256:' .env.images || { echo "CADDY_IMAGE is not digest-pinned" >&2; exit 2; }
fi
docker compose config >/dev/null; fi
printf '\nPreflight: PASS (static/runtime-independent checks)\n'
