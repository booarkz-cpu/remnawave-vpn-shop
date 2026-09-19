#!/usr/bin/env bash
set -Eeuo pipefail
APP_DIR="${APP_DIR:-/opt/vpn-shop}"
cd "$APP_DIR"
[[ -f .env ]] || { echo "Missing .env" >&2; exit 2; }
cp .env ".env.pre-secret-rotation.$(date -u +%Y%m%dT%H%M%SZ)"
current="$(grep -E '^APP_SECRET=' .env | head -1 | cut -d= -f2- || true)"
[[ ${#current} -ge 32 ]] || { echo "APP_SECRET is missing/too short" >&2; exit 2; }
new="$(openssl rand -hex 32)"
python3 - "$current" "$new" <<'PY'
from pathlib import Path
import sys
p=Path('.env'); s=p.read_text(); old,new=sys.argv[1:]
lines=[]
for line in s.splitlines():
    if line.startswith('APP_SECRET_PREVIOUS='): lines.append('APP_SECRET_PREVIOUS='+old)
    elif line.startswith('APP_SECRET='): lines.append('APP_SECRET='+new)
    elif line.startswith('METRICS_TOKEN='): lines.append('METRICS_TOKEN='+__import__('secrets').token_urlsafe(32))
    else: lines.append(line)
p.write_text('\n'.join(lines)+'\n')
PY
# Keep old key for at least token TTL; restart is intentionally required.
docker compose up -d --force-recreate backend worker bot admin miniapp caddy
./scripts/doctor.sh
printf 'Secrets rotated. Previous APP_SECRET remains available for legacy token/secret decryption; remove APP_SECRET_PREVIOUS only after all old tokens have expired.\n'
