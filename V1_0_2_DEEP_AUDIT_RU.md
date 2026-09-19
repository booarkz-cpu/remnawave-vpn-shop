# V1.0.2-realise — очень глубокий аудит и исправления

## Результат

Проведён baseline-аудит релиза `1.0.1-realise` по исходному коду, тестам, бизнес-логике, конкурентному доступу, платежам, webhook/reconciliation, Redis locks, backup/restore, authentication/RBAC, SSRF/DNS, файловым операциям и release tooling. Методика ориентирована на OWASP Secure Code Review: отдельная проверка state transitions, race conditions, transaction integrity и внешних side effects.

## Найдено и исправлено

### CRITICAL/IMPORTANT — auto-renew → fulfillment deadlock

`auto_renew_scheduler` уже держит пользовательский distributed lock, чтобы сериализовать charge с account deletion. После успешной оплаты он вызывал `fulfill()`, а `fulfill()` пытался получить **тот же lock повторно**. В результате успешный recurring payment мог оставаться `paid`, а provisioning завершался ошибкой `User provisioning/deletion is already in progress`.

Исправление: `fulfill()` теперь принимает уже удерживаемый user-lock token и повторно его не захватывает. Auto-renew передаёт существующий token в fulfillment, поэтому lock непрерывно защищает критическую секцию от charge до Remnawave provisioning.

Добавлены regression tests, фиксирующие отсутствие повторного lock acquisition.

### LOW/RELIABILITY — cleanup lock renewal registry

Release helper раньше мог не удалить запись из `_LOCK_RENEW_TASKS`, если Redis становился недоступен в момент release. Теперь renewal task извлекается и отменяется до проверки доступности Redis. Это исключает накопление stale task references.

## Повторно проверено

- DB-enforced payment idempotency;
- durable payment intents и provider idempotency;
- webhook provider/order binding;
- refund/fulfillment serialization;
- trial/account deletion race;
- auto-renew/account deletion race;
- referral reward/refund reversal;
- device-limit concurrency;
- privacy deletion;
- admin MFA/RBAC/session invalidation;
- request-body limits и uploads;
- archive traversal;
- SSRF/DNS-rebinding protection;
- backup/restore locks и path validation;
- Alembic migration chain;
- release/checksum tooling.

## Verification

- **236 tests — PASS**
- Python `compileall` — PASS
- shell syntax — PASS
- Docker Compose YAML parse — PASS
- ZIP integrity — PASS
- SHA-256 verification — PASS

Migration head остаётся `0031_v1_0_0_idempotency_integrity`: V1.0.2 не меняет схему БД, поэтому новая migration не требуется.

## Ограничения

Live production E2E с реальными credentials платёжных провайдеров и живым Remnawave не выполнялся. Полный Vite production build также не заявляется без установленных frontend dependencies; исходный TS/TSX regression/transpile checks остаются частью предыдущей верификации.

## Методология

OWASP рекомендует baseline review для major releases и отдельно подчёркивает анализ бизнес-логики, state transitions, concurrency/race conditions и transaction integrity. citeturn0search0turn0search1
