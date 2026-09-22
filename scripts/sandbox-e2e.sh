#!/usr/bin/env bash
# Sandbox end-to-end checks without live payment gateways.
# Requires a running API with PAYMENTS_SANDBOX=true and at least one enabled plan.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "FAIL: python3 is required" >&2
  exit 1
fi

API_BASE="${SANDBOX_API_BASE:-http://127.0.0.1:8000}"
EMAIL="${SANDBOX_EMAIL:-sandbox-$(date +%s)@example.test}"
PASSWORD="${SANDBOX_PASSWORD:-SandboxPass123!}"
PLAN_ID="${SANDBOX_PLAN_ID:-}"
COOKIE_JAR="$(mktemp)"
trap 'rm -f "$COOKIE_JAR"' EXIT

echo "[sandbox] API: $API_BASE"

health=$(curl -fsS --max-time 15 "$API_BASE/health")
"$PYTHON" - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1])
if not x.get("ok"):
    raise SystemExit("FAIL: /health is not ok")
print(f"[PASS] health ok version={x.get('version')}")
PY

cfg=$(curl -fsS --max-time 15 "$API_BASE/api/public/config")
"$PYTHON" - "$cfg" <<'PY'
import json,sys
cfg=json.loads(sys.argv[1])
if not cfg.get("payments_sandbox"):
    raise SystemExit("FAIL: PAYMENTS_SANDBOX is not enabled on the server")
providers=[str(p).lower() for p in (cfg.get("payment_providers") or [])]
if "sandbox" not in providers:
    raise SystemExit(f"FAIL: sandbox provider missing from payment_providers={providers}")
print("[PASS] public config exposes sandbox provider")
PY

menu=$(curl -fsS --max-time 15 "$API_BASE/api/public/cabinet-menu")
"$PYTHON" - "$menu" <<'PY'
import json,sys
rows=json.loads(sys.argv[1])
if not isinstance(rows,list) or not rows:
    raise SystemExit("FAIL: cabinet menu empty")
print(f"[PASS] cabinet menu items={len(rows)}")
PY

csrf=$("$PYTHON" - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)

curl -fsS --max-time 20 -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -X POST "$API_BASE/api/auth/register" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $csrf" \
  -H "Cookie: rw_csrf=$csrf" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" >/tmp/sandbox-register.json

"$PYTHON" - <<'PY'
import json
d=json.load(open("/tmp/sandbox-register.json"))
if not d.get("id"):
    raise SystemExit(f"FAIL: register response={d}")
print(f"[PASS] registered user id={d['id']} email={d.get('email')}")
PY

# Refresh CSRF from jar after auth cookies are set
csrf=$("$PYTHON" - "$COOKIE_JAR" <<'PY'
import sys
csrf=""
for line in open(sys.argv[1]):
    if line.startswith("#") or not line.strip():
        continue
    parts=line.split("\t")
    if len(parts)>=7 and parts[5]=="rw_csrf":
        csrf=parts[6].strip()
print(csrf)
PY
)
[[ -n "$csrf" ]] || { echo "FAIL: rw_csrf cookie missing after register"; exit 2; }

if [[ -z "$PLAN_ID" ]]; then
  plans=$(curl -fsS --max-time 15 -b "$COOKIE_JAR" "$API_BASE/api/plans")
  PLAN_ID=$("$PYTHON" - "$plans" <<'PY'
import json,sys
rows=json.loads(sys.argv[1])
if not rows:
    raise SystemExit("FAIL: no plans available; create one in admin or set SANDBOX_PLAN_ID")
print(rows[0]["id"])
PY
  )
fi
echo "[sandbox] using plan_id=$PLAN_ID"

idem="sandbox-e2e-$(date +%s)-$RANDOM"
pay=$(curl -fsS --max-time 30 -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  -X POST "$API_BASE/api/payments/create" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $idem" \
  -H "X-CSRF-Token: $csrf" \
  -d "{\"plan_id\":$PLAN_ID,\"provider\":\"sandbox\"}")

"$PYTHON" - "$pay" <<'PY'
import json,sys
d=json.loads(sys.argv[1])
if not d.get("id"):
    raise SystemExit(f"FAIL: payment create={d}")
print(f"[PASS] sandbox payment created id={d.get('id')} status={d.get('status')} url={d.get('url')}")
open("/tmp/sandbox-payment.json","w").write(json.dumps(d))
PY

payment_id=$("$PYTHON" - <<'PY'
import json
print(json.load(open("/tmp/sandbox-payment.json")).get("id") or "")
PY
)

complete=$(curl -fsS --max-time 30 -b "$COOKIE_JAR" \
  -X POST "$API_BASE/api/payments/sandbox/complete" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $csrf" \
  -d "{\"payment_id\":\"$payment_id\"}")
"$PYTHON" - "$complete" <<'PY'
import json,sys
d=json.loads(sys.argv[1])
if not d.get("ok"):
    raise SystemExit(f"FAIL: sandbox complete={d}")
print(f"[PASS] sandbox complete fulfillment={d.get('fulfillment_status')}")
PY

dash=$(curl -fsS --max-time 15 -b "$COOKIE_JAR" "$API_BASE/api/me/dashboard")
"$PYTHON" - "$dash" <<'PY'
import json,sys
d=json.loads(sys.argv[1])
sub=d.get("subscription") or {}
print(f"[PASS] dashboard loaded user={d.get('user',{}).get('id')} subscription_plan={sub.get('plan_id')}")
PY

servers=$(curl -fsS --max-time 15 "$API_BASE/api/public/servers")
"$PYTHON" - "$servers" <<'PY'
import json,sys
d=json.loads(sys.argv[1])
blob=json.dumps(d).lower()
for forbidden in ("address","hostname","token","password","private"):
    if f'"{forbidden}"' in blob:
        raise SystemExit(f"FAIL: public server status leaked {forbidden}")
if "nodes" not in d or "ok" not in d:
    raise SystemExit(f"FAIL: public servers payload={d}")
print(f"[PASS] public server status ok={d.get('ok')} nodes={d.get('total')}")
PY

ctors=$(curl -fsS --max-time 15 "$API_BASE/api/tariff-constructors")
"$PYTHON" - "$ctors" <<'PY'
import json,sys
d=json.loads(sys.argv[1])
if not isinstance(d, list):
    raise SystemExit(f"FAIL: constructors payload={d}")
print(f"[PASS] tariff constructors listed count={len(d)}")
PY

echo "[PASS] sandbox e2e finished without live payment gateways"
echo "[NEXT] Optional: open CABINET_URL, sign in with $EMAIL, check connection tab."
