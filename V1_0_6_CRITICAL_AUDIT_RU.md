# V1.0.6-realise — Critical Audit

Дата: 2026-09-14
Предыдущий релиз: 1.0.5-realise

## Результат

В ходе критического повторного аудита обнаружена и исправлена **критическая ошибка порядка распределённых блокировок** в refund workflow.

### Критическая ошибка: `payment -> user` против `user -> payment`

Основной fulfillment workflow использует единый порядок:

`user lock -> payment lock -> DB row locks -> external provisioning`

Однако несколько refund/reconciliation путей ранее брали `payment lock`, а затем внутри `_safe_revoke_for_refunded_payment()` получали `Subscription` через `SELECT ... FOR UPDATE`. Параллельно `fulfill()` мог уже удерживать `user lock` и ждать `payment lock`.

Это создавало классический deadlock/race сценарий:

1. fulfillment удерживает `user lock` и ждёт `payment lock`;
2. refund удерживает `payment lock` и пытается получить user/subscription row lock;
3. оба workflow могут зависнуть/конфликтовать, а финансовое состояние и provisioning могут остаться в retry/reconciliation.

OWASP отдельно относит подобные check-then-act и concurrency ошибки к критическим областям ручного business-logic review. См. OWASP Secure Code Review и Business Logic Security Cheat Sheet.

## Исправление

Все refund-side-effect entry points теперь используют **строго одинаковый порядок**:

1. `lock:fulfill:user:<user_id>`;
2. `lock:fulfill:payment:<payment_id>`;
3. повторное `SELECT ... FOR UPDATE` актуальных `Payment` и `RefundRequest`;
4. subscription/revoke операции;
5. внешний Remnawave side effect;
6. release payment lock;
7. release user lock.

Исправлены все четыре пути:

- background `refund_revoke_scheduler`;
- admin `execute_refund`;
- admin `retry_refund_revoke`;
- admin `reconcile_refund`.

Добавлены regression checks, которые фиксируют invariant порядка locks и повторное чтение финансовых сущностей после захвата обоих locks.

## Повторная проверка

- **247 тестов — PASS**
- `python -m compileall -q backend` — PASS
- `bash -n install.sh deploy/*.sh scripts/*.sh` — PASS
- Docker Compose YAML parse — PASS
- ZIP integrity — PASS
- SHA-256 — PASS

## Scope

Повторно просмотрены критические цепочки:

- payment creation/idempotency;
- provider webhooks;
- fulfillment/provisioning;
- refund execution/reconciliation/revoke;
- auto-renew;
- account deletion/privacy;
- referral reward/reversal;
- Redis distributed locks and lease renewal;
- authentication/session/RBAC;
- request/upload/archive limits;
- SSRF/DNS pinning;
- backup/restore;
- migration/release tooling.

## DB

Migration head остаётся:

`0031_v1_0_0_idempotency_integrity`

Новая schema migration для V1.0.6 не требуется.

## Ограничения

Live production E2E с реальными payment credentials и живым Remnawave в этой среде не выполнялся. Полный frontend Vite production build без установленных frontend dependencies также не заявляется.
