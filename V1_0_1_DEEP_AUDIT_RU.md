# V1.0.1 Realise — очень глубокий аудит и исправления

## Результат

Проведён повторный baseline-аудит проекта после V1.0.0 с приоритетом на бизнес-логику, concurrency/race conditions, state transitions, внешние side effects, Redis distributed locks, уведомления, платежи, webhooks, privacy, backup/restore, authentication/RBAC, SSRF/DNS pinning и release tooling.

### Найдено и исправлено

#### HIGH — утечка задач продления Redis-lock
В V1.0.0 часть lock-release путей удаляла Redis key напрямую через Lua, минуя `_LOCK_RENEW_TASKS`. Renewal task оставался зарегистрированным до следующего lease-expiry, что при большом количестве fulfillment/payment operations приводило к накоплению asyncio tasks и лишней нагрузке.

Исправление: все release-пути переведены на `_release_payment_side_effect_lock()`, который сначала удаляет token из `_LOCK_RENEW_TASKS`, отменяет renewal task и затем token-safe удаляет Redis key.

#### MEDIUM — потеря expiry-уведомления при ошибке Telegram API
Ранее Redis marker с TTL 7 дней устанавливался **до** отправки сообщения. При HTTP 4xx/5xx или сетевой ошибке пользователь мог не получить уведомление, а повторная отправка блокировалась на 7 дней.

Исправление: добавлен короткий `:sending` lease на 5 минут; долгий marker устанавливается только после успешного HTTP ответа. При ошибке sending-marker удаляется.

### Повторно проверено

- payment idempotency и DB unique invariant;
- durable payment intents до внешнего charge;
- provider webhook verification и event idempotency;
- refund ↔ fulfillment serialization;
- auto-renew ↔ deletion serialization;
- trial ↔ deletion serialization;
- Redis lock renewal и token-safe release;
- referral reward/reversal integrity;
- withdrawal balance atomicity;
- device limit race;
- privacy deletion и remote entitlement revocation;
- Telegram/Yandex authentication;
- admin session/MFA/RBAC;
- upload/body limits и archive traversal;
- SSRF protection и DNS rebinding mitigation;
- backup/restore validation;
- staging production-payment gate;
- Alembic migration chain;
- release/install/checksum tooling.

## Проверки

- **232 теста — PASS**
- Python AST/compile checks — PASS
- shell syntax — PASS
- Docker Compose YAML parse — PASS
- ZIP integrity — PASS

Production E2E с реальными payment credentials и live Remnawave в данной среде не заявляется как выполненный. Полный Vite production build не заявляется без frontend dependencies; TS/TSX transpile остаётся отдельной проверкой.

## Релиз

Version: `1.0.1-realise`
Migration head: `0031_v1_0_0_idempotency_integrity`
Previous release: `1.0.0-realise`
