# Remnawave VPN Shop 45.0.0 Enterprise — очень глубокий аудит

## Итог

Проведён полный baseline-аудит релиза 44.5.20 с отдельным adversarial review критических бизнес-workflows, concurrency/TOCTOU, authentication/authorization, uploads, backup/restore, monitoring SSRF, dependencies, worker lifecycle и release tooling.

По итогам аудита найдены и исправлены дополнительные дефекты, влияющие на целостность финансовых и privacy workflow, а также на устойчивость resource limits.

## 🔴 Critical — trial worker ↔ account deletion race

Очередь trial могла выполнять provisioning после того, как пользователь успел пройти privacy deletion, если trial ещё не создал локальную Subscription.

Исправление:
- trial worker использует тот же user-level distributed lock, что и account deletion/fulfillment;
- после получения lock пользователь перечитывается с `FOR UPDATE`;
- `deleted_at` проверяется непосредственно перед внешним Remnawave side effect;
- удалённый trial переводится в `cancelled` без provisioning.

Это закрывает TOCTOU между check account state и external provisioning.

## 🔴 Critical — auto-renew ↔ account deletion race

Scheduler мог выбрать пользователя до deletion и продолжить charge после изменения account state.

Исправление:
- auto-renew получает user-level lock;
- user/method/subscription перечитываются после lock;
- `deleted_at` и `auto_renew_enabled` повторно проверяются непосредственно перед charge;
- deletion и recurring charge используют одну critical section.

## 🔴 Critical — refund revoke retry ↔ fulfillment

Основной refund reconciliation уже использовал payment side-effect lock, но отдельный `refunded_pending_revoke` retry path оставался независимым entry point.

Исправление:
- retry revoke теперь получает тот же payment lock;
- Payment и RefundRequest перечитываются с `FOR UPDATE` после lock;
- состояние повторно проверяется перед revoke;
- referral reversal выполняется внутри той же критической секции.

## 🟠 Important — distributed lock lease expiry

Payment/user locks имели фиксированный TTL 5 минут. Длительный внешний Remnawave/provider operation мог пережить lease, после чего другой worker потенциально мог войти в тот же critical section.

Исправление:
- добавлен token-bound lock renewal;
- lease автоматически продлевается каждые `ttl/3`;
- renewal разрешён только владельцу исходного token;
- release отменяет renewal task и удаляет lock только при совпадении token.

Это делает lock lifetime связанным с фактическим выполнением операции, а не только с первоначальным TTL.

## 🟠 Important — chunked request body bypass

Global `12 MiB` request guard ранее проверял только `Content-Length`. Chunked requests могут не иметь этого заголовка.

Исправление:
- request body без `Content-Length` теперь читается потоково;
- после `MAX_REQUEST_BYTES + 1` запрос отклоняется `413`;
- допустимое тело кэшируется и передаётся дальше обычному FastAPI endpoint.

Таким образом общий resource limit применяется и к chunked HTTP requests.

## DNS-rebinding / TOCTOU

Исправление V44.5.20 сохранено и повторно проверено:

- runtime DNS resolution непосредственно перед TCP connect;
- все A/AAAA ответы проверяются на global/public status;
- TCP connect выполняется к проверенному literal IP;
- hostname сохраняется для TLS SNI/certificate verification;
- redirects отключены;
- `trust_env=False` отключает неожиданные proxy environment variables.

Поэтому public→private DNS rebinding между validation и TCP connection больше не даёт попасть на private/local destination.

OWASP отдельно рекомендует проверять именно race/TOCTOU, workflow state, transaction integrity и resource limits при secure code review. См. OWASP Secure Code Review и Business Logic Security Cheat Sheets.

## Повторно проверенные критические области

- payment intent/idempotency;
- provider webhook binding;
- amount/currency/order verification;
- late webhook after refund;
- refund ↔ fulfillment;
- refund reconciliation ↔ fulfillment;
- auto-renew ↔ refund;
- referral balance/withdrawal/payout;
- promo reservation;
- trial lifecycle;
- Remnawave provisioning/recovery/revoke;
- account deletion/privacy lifecycle;
- JWT/session invalidation;
- MFA/RBAC/CSRF;
- upload validation and limits;
- branding assets;
- backup/restore/archive traversal;
- monitoring SSRF/DNS rebinding;
- Alembic/release tooling;
- dependency pinning;
- admin frontend theme/branding.

## Verification

- `pytest -q` → **225 passed**
- `python -m compileall -q backend` → PASS
- `bash -n install.sh deploy/*.sh scripts/*.sh` → PASS
- Docker Compose YAML parse → PASS
- TypeScript/TSX transpilation → PASS
- DNS-pinning regression tests → PASS
- ZIP integrity → PASS
- detached SHA-256 manifest → PASS
- release version consistency → PASS

## Limitations

Production YooKassa/Platega/RollyPay E2E и live Remnawave API требуют внешнего staging/production окружения и credentials; они не заявляются как выполненные здесь.

Полный browser/Vite production build требует установки frontend dependencies. Source-level TSX transpilation проходит.

## Release

**Version:** 45.0.0-enterprise

**Migration head:** `0030_v44_5_16_privacy_and_refund_integrity`

Schema migration для исправлений этого релиза не потребовалась.
