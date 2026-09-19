# V1.0.3-realise — глубокий аудит и исправления

Проведён повторный baseline-аудит релиза `1.0.2-realise` по исходному коду и тестам. Фокус: бизнес-логика, state transitions, race conditions, transaction integrity, distributed locks, authentication, внешние side effects, backup/restore, платежи и release tooling. Методика опирается на OWASP Secure Code Review и Business Logic Security: отдельная проверка конкурентного доступа, атомарности, workflow/state и внешних non-idempotent side effects.

## Найдено и исправлено

### IMPORTANT — lifecycle утечки Redis lock renewal tasks

Renewal task ранее удалялся из `_LOCK_RENEW_TASKS` только через внешний release helper. Если владелец lock зависал, терял Redis или renewal task завершался раньше владельца, ссылка могла оставаться в глобальном registry неопределённо долго.

Исправление: `_renew_redis_lock()` теперь выполняет self-cleanup в `finally`, удаляя запись только если registry всё ещё указывает на тот же asyncio task. Это не влияет на token-safe release и не позволяет удалить registry entry нового владельца.

### NORMAL/IMPORTANT — malformed Telegram initData мог приводить к 500

`auth_date` разбирался через голый `int()`, а структура подписанного `user` JSON не проверялась до обращения к `id` в вызывающем коде.

Исправление:
- нечисловой/отсутствующий `auth_date` возвращает `401`;
- `user` обязан быть объектом;
- Telegram `id` обязан существовать и быть приводимым к integer;
- ошибки malformed signed payload fail-closed через `401`.

## Повторно проверено

- payment idempotency и DB unique constraint;
- durable payment intents;
- provider webhook binding и replay protection;
- fulfillment/payment/refund concurrency;
- auto-renew и account deletion;
- trial и account deletion;
- referral ledger/reversal;
- promo reservations;
- device-limit concurrency;
- privacy deletion;
- Telegram/Yandex authentication и exchange-code replay;
- MFA/RBAC/admin sessions;
- Redis lock acquisition/renewal/release;
- backup/restore and maintenance locking;
- SSRF/DNS pinning;
- request/body/file/archive limits;
- Alembic migration chain;
- release/install/checksum tooling.

## Verification

- полный `pytest -q` — ожидается после сборки релиза;
- `compileall` — выполняется build script;
- shell syntax — выполняется build script;
- Docker Compose YAML parse — выполняется build script;
- ZIP integrity — выполняется build script;
- detached SHA-256 manifest — генерируется после сборки.

Migration head остаётся `0031_v1_0_0_idempotency_integrity`; схема БД для V1.0.3 не менялась.

Production E2E с реальными credentials платёжных провайдеров и живым Remnawave в данной среде не заявляется выполненным. Полный Vite production build также не заявляется без frontend dependencies.
