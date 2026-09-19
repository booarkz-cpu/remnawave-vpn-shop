#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export COMPOSE_FILE="docker-compose.yml:docker-compose.integration.yml"
trap 'docker compose down -v' EXIT
docker compose build backend worker
docker compose up -d db redis backend worker
docker compose run --rm backend alembic upgrade head
curl --fail --retry 20 --retry-delay 2 http://localhost:18000/health >/dev/null
docker compose exec -T backend python -m pytest -q tests
printf 'Integration smoke test passed.\n'
