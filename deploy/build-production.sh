#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f .env ]] || { echo "Missing .env. Run deploy/install-vps.sh first."; exit 2; }
./scripts/preflight.sh
if command -v docker >/dev/null 2>&1; then
  if [[ -f .env.images ]]; then set -a; . ./.env.images; set +a; fi
  docker compose config >/dev/null
  if [[ "${FULL_REBUILD:-1}" == "1" ]]; then docker compose build --pull --no-cache; else docker compose build --pull; fi
  docker compose up -d --remove-orphans
  for i in {1..80}; do
    if docker compose exec -T backend python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3)' >/dev/null 2>&1; then
      for svc in admin miniapp cabinet; do
        docker compose exec -T "$svc" curl -fsS http://127.0.0.1/ >/dev/null || { docker compose logs --tail=80 "$svc" >&2; echo "$svc did not serve HTTP" >&2; exit 1; }
      done
      docker compose ps
      exit 0
    fi
    sleep 3
  done
  docker compose ps
  docker compose logs --tail=120 backend worker
  echo "Backend did not become healthy" >&2
  exit 1
else
  echo "Docker daemon unavailable: static preflight passed; container runtime build skipped." >&2
fi
