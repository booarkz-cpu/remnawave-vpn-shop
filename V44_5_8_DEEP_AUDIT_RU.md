# V44.5.8 — Very Deep Multi-System Audit / Fixed

## Scope

Повторно проверены backend API, платежи, webhook/reconciliation, fulfillment, Remnawave provisioning, referrals, promo reservations, withdrawals, auto-renew, trial worker, admin authentication/MFA, backups/restore, CMS/media, monitoring, migrations и release tooling.

## Новые исправления

### HIGH — повторное продление Remnawave после неопределённого ответа

ProvisioningOperation уже сохранял `expected_before_expires_at` / `expected_after_expires_at`, но повторный запуск пересчитывал target от текущей удалённой даты. Если предыдущий `extend` прошёл на Remnawave, а локальная транзакция затем откатилась, retry мог выдать второй срок.

Исправление:
- retry использует сохранённый target операции;
- `RemnawaveClient.extend_idempotent()` считает `current >= expected_after` уже выполненной операцией;
- если remote expiry неожиданно находится между `expected_before` и `expected_after`, повторное продление запрещается и операция уходит в reconciliation вместо риска двойной выдачи.

### HIGH — entitlement старого плана мог сохраняться после покупки нового

При продлении существующего Remnawave user срок обновлялся, но traffic quota/profile могли остаться от предыдущего тарифа.

Исправление:
- перед extension применяются `trafficLimitBytes` и `activeInternalSquads` из snapshot оплаченного Payment;
- добавлен `update_entitlements()`.

### HIGH — лимит устройств зависел от текущего Plan

После изменения тарифа администратором уже купленная подписка могла внезапно получить новый `device_limit`.

Исправление:
- Subscription теперь хранит immutable entitlement snapshots:
  - `traffic_limit_gb_snapshot`
  - `device_limit_snapshot`
  - `remnawave_profile_id_snapshot`
- registration устройства использует snapshot активной подписки;
- trial также фиксирует entitlement.

### MEDIUM/HIGH — recovery code MFA мог быть использован дважды при гонке

Два параллельных login request могли прочитать один и тот же recovery code до commit.

Исправление: admin row блокируется `SELECT ... FOR UPDATE` на время проверки и consumption recovery code.

### MEDIUM — refund в состоянии review нельзя было реально retry

Endpoint разрешал `review` в первом state-check, но после lock принимал только `requested/approved`.

Исправлено: `review` корректно переводится в `processing` и повторяется с тем же provider idempotency key.

## Regression tests

**166 тестов — 166 passed.**

Добавлен `tests/test_v44_5_8_deep_regressions.py`.

## Static / release checks

- Python compile/AST — PASS
- pytest — PASS
- Bash syntax — PASS
- Docker Compose YAML parse — PASS
- migration chain inspected — PASS
- release version consistency — PASS
- ZIP integrity — PASS
- SHA-256 manifest — PASS

## Ограничения

Реальные production payment credentials, live Remnawave API, production Docker runtime и внешний staging E2E недоступны в sandbox. Поэтому они не обозначены как пройденные.

## Методология

Аудит ориентирован на server-side invariants, state transitions, race conditions, transaction atomicity и idempotency, поскольку именно такие business-logic дефекты часто не выявляются обычным автоматическим сканированием.
