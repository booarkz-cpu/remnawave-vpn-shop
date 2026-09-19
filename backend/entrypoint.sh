#!/bin/sh
set -eu
alembic upgrade head
if [ "${WORKER_ROLE:-api}" = "worker" ]; then
  exec "$@"
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="172.16.0.0/12,10.0.0.0/8,127.0.0.1"
