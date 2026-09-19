# Критический аудит V1.0.8-realise

## Результат

Проведён новый критический аудит исходников V1.0.7-realise с фокусом на финансовые state transitions, race conditions/TOCTOU, distributed locks и внешние side effects. OWASP рекомендует для baseline review отдельно трассировать бизнес-логику, state transitions, concurrency, transaction integrity и configuration/deployment controls.

## Критическая находка — исправлена

### Stale success confirmation мог воскресить refunded Payment

До исправления webhook/reconciliation paths сначала читали `Payment`, проверяли успешный ответ провайдера, а затем могли присвоить локальному объекту `status="paid"`. Между этими действиями refund/reconciliation другого процесса мог изменить запись на `refunded`.

Опасный сценарий:

1. reconciliation/webhook читает `pending`;
2. провайдер подтверждает успешную оплату;
3. конкурентный refund завершает `Payment -> refunded`;
4. старый reconciliation snapshot выполняет `Payment -> paid`;
5. запускается fulfillment уже для возвращённого платежа.

Это нарушает финансовый инвариант: **refunded Payment не должен возвращаться в paid и не должен запускать provisioning**.

### Исправление

Добавлен единый `_confirm_and_fulfill_payment()`:

- захватывает user lock;
- затем payment side-effect lock;
- перечитывает `Payment` через `SELECT ... FOR UPDATE`;
- отклоняет `refunded`, `refunded_pending_revoke` и `creation_unknown`;
- только после актуальной проверки переводит запись в `paid`;
- сохраняет user lock при переходе к `fulfill()`;
- `fulfill()` повторно защищён собственным payment-lock и актуальным `FOR UPDATE` чтением.

Единый порядок критических locks остаётся: **user → payment**.

### Затронутые пути

- YooKassa webhook;
- Platega webhook;
- RollyPay webhook;
- manual admin payment reconciliation;
- background reconciliation scheduler.

### Regression coverage

Добавлены `tests/test_v1_0_8_critical_regression.py` с проверкой:

- lock order;
- `FOR UPDATE` re-read перед paid transition;
- блокировки refunded/creation_unknown;
- отсутствие прямого stale `p.status="paid"` в reconciliation/webhook paths;
- делегирование fulfillment единому atomic helper.

## Верификация

- **252 теста — PASS**
- Python `compileall` — PASS
- shell syntax — PASS
- Docker Compose YAML parse — PASS
- ZIP integrity — PASS
- SHA-256 — PASS

Migration head: `0031_v1_0_0_idempotency_integrity`.

Новая DB migration для V1.0.8 не требуется: изменение относится к application-level concurrency/transaction control.

## Ограничения

Production E2E с реальными credentials платёжных провайдеров и живым Remnawave в этой среде не выполнялся. Полный Vite production build без установленных frontend dependencies не заявляется; TS/TSX static/transpile checks остаются отдельной проверкой.
