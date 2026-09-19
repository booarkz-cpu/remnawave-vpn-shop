# Remnawave VPN Shop — V44.5.14 Enterprise Deep Audit

## Итог

Проведён повторный глубокий аудит исходного проекта V44.5.13 с приоритетом на финансовую целостность, state machines, concurrency/idempotency, authentication/authorization, SSRF, uploads, backup/restore, release tooling и зависимости. По результатам исправлены найденные дефекты и подготовлен V44.5.14.

## Найденные и исправленные дефекты

### CRITICAL

Критических дефектов, позволяющих напрямую получить бесплатную подписку, двойное списание или произвольное выполнение действий без требуемой авторизации, в проверенной логике не обнаружено. Ранее исправленные payment/webhook/refund/provisioning invariants повторно проверены regression-тестами.

### HIGH / IMPORTANT

1. **Trial с неопределённым expiry подписки.** Проверка trial учитывала только `expires_at > now`; legacy/корректно созданная подписка с `expires_at=NULL` могла трактоваться как отсутствие активной подписки. Теперь `NULL` expiry считается активной/неограниченной подпиской и trial блокируется.
2. **Chunked multipart upload мог обходить общий Content-Length лимит.** Три upload endpoint уже имели bounded read, но background image и menu image имели путь `await file.read()` без ограничения. Это позволяло authenticated admin отправить chunked multipart с чрезмерным объёмом и создать memory/CPU pressure. Добавлен единый `_read_upload_limited()` и убраны unbounded reads.
3. **Устаревшие security-sensitive зависимости.** Обновлены `PyJWT` до 2.13.0, `python-multipart` до 0.0.31, `Paramiko` до 5.0.0, `boto3` до 1.43.91; неиспользуемый `Authlib` удалён. Для python-multipart опубликованы актуальные advisory, включая DoS/parser differential issues для версий до fixed releases.

### NORMAL

4. Дублированное чтение menu image после первоначального ограничения устранено: файл теперь читается один раз с верхней границей.
5. Release metadata/tooling обновлены с 44.5.13 до 44.5.14.

## Повторно проверенные области

- Payment durable intents и idempotency.
- Provider routing/circuit breaker.
- YooKassa/Platega/RollyPay webhooks и event deduplication.
- Refund state machine, retry/revoke и referral clawback.
- Promo reservations.
- Trial claim/worker.
- Remnawave entitlement snapshots/recovery/extension.
- Device-limit concurrency.
- Auth exchange single-use locking.
- Admin sessions, MFA, recovery codes, CSRF/RBAC.
- Backup archive traversal/symlink checks, checksum and restore workflow.
- Monitoring SSRF validation.
- File uploads.
- Docker hardening and Alembic chain.

OWASP отдельно рекомендует при code review анализировать business workflows, state transitions, race conditions, transaction integrity и idempotency, а не ограничиваться сигнатурными уязвимостями. citeturn0search0turn0search1

## Проверки

- `pytest -q`: **200 passed**
- Python compile check: должен быть выполнен перед release build
- Shell syntax: должен быть выполнен перед release build
- ZIP integrity: должен быть проверен после сборки
- Реальные production payment/Remnawave E2E здесь не заявляются без production/staging credentials.

## Dependency research

`python-multipart` 0.0.20 был существенно устаревшим относительно актуальных 2026 advisory; для ряда parser/DoS проблем исправления находятся в 0.0.30/0.0.31+. citeturn2search0turn2search6turn2search7

`Paramiko` 5.0.0 доступен с мая 2026; текущий проект использует SSH provisioning и поэтому dependency maintenance является security-sensitive. citeturn4search5

## Остаточные ограничения

- DNS TOCTOU в hostname-based monitoring не может быть полностью устранён простой предварительной DNS-проверкой; текущая реализация запрещает private/local resolution и отключает redirects, но полноценный DNS pinning требует транспортного уровня.
- Production provider APIs и Remnawave API недоступны в среде аудита.
- Docker runtime и browser production builds требуют соответствующей CI/runtime инфраструктуры.
