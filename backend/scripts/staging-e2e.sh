#!/usr/bin/env bash
set -Eeuo pipefail
command -v curl >/dev/null 2>&1 || { echo 'FAIL: в контейнере backend нет curl' >&2; exit 2; }
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
: "${STAGING_PUBLIC_BASE_URL:?Укажите публичный HTTPS URL staging}"
: "${STAGING_REMNAWAVE_URL:?Укажите HTTPS URL staging Remnawave}"
: "${STAGING_REMNAWAVE_TOKEN:?Не задан токен staging Remnawave}"
: "${STAGING_PLAN_ID:?Не задан ID тестового тарифа}"
: "${STAGING_RUNNER_TOKEN:?Не задан внутренний токен runner}"
STAGING_TIMEOUT_SECONDS="${STAGING_TIMEOUT_SECONDS:-1800}"
STAGING_PROVIDERS="${STAGING_PROVIDERS:-yookassa,platega,rollypay}"

case "$STAGING_PUBLIC_BASE_URL" in https://*) ;; *) echo 'FAIL: публичный URL должен использовать HTTPS' >&2; exit 2;; esac
case "$STAGING_REMNAWAVE_URL" in https://*) ;; *) echo 'FAIL: URL Remnawave должен использовать HTTPS' >&2; exit 2;; esac

health=$(curl -fsS --location --max-redirs 0 --proto "=https" --proto-redir "=https" --retry 10 --retry-delay 2 --max-time 20 "$STAGING_PUBLIC_BASE_URL/health")
python - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1])
for k in ('database','redis'):
    if not x.get(k): raise SystemExit(f'FAIL: {k} недоступен')
if not x.get('ok'): raise SystemExit('FAIL: backend health degraded')
print('[PASS] PostgreSQL + Redis + backend health')
PY

if curl -fsS --max-redirs 0 --proto "=https" --proto-redir "=https" --retry 5 --retry-delay 2 --max-time 20 \
  -H "Authorization: Bearer $STAGING_REMNAWAVE_TOKEN" \
  "$STAGING_REMNAWAVE_URL" >/dev/null 2>&1; then
  echo '[PASS] Remnawave endpoint доступен'
else
  echo '[WARN] Корневой endpoint Remnawave не подтвердил доступ; продолжение через платёжный E2E.'
fi

IFS=',' read -r -a providers <<< "$STAGING_PROVIDERS"
for provider in "${providers[@]}"; do
  [[ -n "$provider" ]] || continue
  case "$provider" in yookassa|platega|rollypay) ;; *) echo "FAIL: неизвестный провайдер $provider"; exit 2;; esac
  idem="staging-e2e-${provider}-$(date +%s)-$RANDOM"
  echo "[RUN] $provider: создание sandbox-платежа через приложение"
  body=$(curl -fsS --max-redirs 0 --proto "=http" --retry 3 --retry-delay 1 --max-time 30 \
    -X POST "http://127.0.0.1:8000/api/internal/staging-e2e/payment" \
    -H "X-Staging-Runner-Token: $STAGING_RUNNER_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"plan_id\":$STAGING_PLAN_ID,\"provider\":\"$provider\"}")
  python - "$provider" "$body" <<'PY'
import json,sys
provider=sys.argv[1]; d=json.loads(sys.argv[2])
if not d.get('id') or not str(d.get('url') or '').startswith('https://'):
    raise SystemExit(f'FAIL {provider}: приложение не вернуло id и https checkout')
print(f'[PASS] {provider}: платёж создан, id={d["id"]}')
print(f'[CHECKOUT] {provider} {d["url"]}')
print('[ACTION] Откройте строку CHECKOUT в журнале панели и завершите sandbox-оплату.')
PY
done

echo '[PASS] Создание staging-платежей для всех выбранных провайдеров завершено.'
echo '[NEXT] Для каждого провайдера подтвердите: sandbox-оплата -> подписанный webhook -> проверка статуса/суммы -> paid -> worker -> Remnawave -> повторный webhook без двойной выдачи -> refund -> отзыв/восстановление.'
echo '[GATE] Статус awaiting_checkout не включает production gate. Кнопка «Разрешить реальные платежи» ждёт строку FULL_E2E_PASS не старше 24 часов.'
