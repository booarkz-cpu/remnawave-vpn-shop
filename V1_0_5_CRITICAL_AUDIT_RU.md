# V1.0.5-realise — критический аудит и исправления

Дата: 2026-09-14

## 1. Область аудита

Проверены критические денежные и stateful workflow: payment → fulfillment → refund/reconcile → provisioning, auto-renew, account deletion, distributed locks, backup/restore, authentication, authorization и release tooling.

Методика включает ручную трассировку state transitions, check-then-act участков, порядка distributed locks и внешних side effects. Это соответствует OWASP Secure Code Review и Business Logic Security guidance.

## 2. Найденная критическая ошибка

### CRITICAL — stale payment snapshot после получения payment lock

`fulfill()` сначала читал Payment и видел `paid`, а затем отдельно получал payment lock. Между этими действиями refund/reconciliation мог получить тот же lock и перевести платёж в `refunded`.

После освобождения lock `fulfill()` продолжал использовать старый объект Payment со статусом `paid` и мог начать внешний Remnawave provisioning. Финальная проверка в конце workflow обнаруживала уже изменённый статус, но remote side effect к этому моменту мог быть выполнен.

Это нарушение критического инварианта:

**refunded payment → не должен создавать или продлевать remote entitlement.**

### Исправление

После получения общего payment lock `fulfill()` теперь обязательно:

1. перечитывает Payment через `SELECT ... FOR UPDATE`;
2. повторно проверяет `status`;
3. отклоняет `refunded`, `refunded_pending_revoke`, `creation_unknown`;
4. разрешает provisioning только при актуальном `paid`;
5. только после этого переводит fulfillment в `processing` и создаёт внешний side effect.

Таким образом, check и side effect выполняются относительно актуального состояния внутри общей критической секции.

## 3. Регрессионные тесты

Добавлен `tests/test_v1_0_5_critical_regressions.py`:

- проверяет reload Payment после acquisition payment lock;
- проверяет, что reload происходит до создания Remnawave client/remote side effect;
- проверяет rejection refunded states;
- проверяет token-safe release.

## 4. Проверка релиза

- **245 тестов — PASS**
- Python `compileall` — PASS
- shell syntax — PASS
- Docker Compose YAML parse — PASS
- ZIP integrity — PASS
- SHA-256 — PASS

## 5. Повторно проверенные критические контуры

- durable payment intents;
- DB idempotency;
- provider/order binding;
- webhook replay protection;
- refund execution/reconciliation;
- fulfillment retries;
- auto-renew;
- account deletion;
- user/payment lock ordering;
- Redis lock renewal/token ownership;
- Remnawave provisioning idempotency;
- backup checksum/archive safety/isolated restore;
- Telegram/Yandex authentication;
- MFA/RBAC;
- SSRF/DNS pinning;
- request/upload limits.

## 6. Database

Новая migration для исправления не требуется.

Migration head:

`0031_v1_0_0_idempotency_integrity`

## 7. Ограничения

Не заявляются как выполненные в этой среде:

- live production payment E2E с реальными credentials;
- live Remnawave production E2E;
- полный Vite production build без установленных frontend dependencies.

## 8. Итог

Критический stale-state race в fulfillment устранён. После получения payment lock состояние платежа повторно фиксируется через row lock до любого внешнего provisioning side effect.

Релиз: **1.0.5-realise**.
