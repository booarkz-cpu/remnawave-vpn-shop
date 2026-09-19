# V1.0.0 Realise — очень глубокий аудит и исправления

## Итог

Проведён baseline-аудит текущей кодовой базы после V45 с повторной проверкой критических денежных, конкурентных, аутентификационных, административных, backup/restore и внешних интеграционных потоков.

### Результат

- Релиз: **1.0.0-realise**
- Migration head: **0031_v1_0_0_idempotency_integrity**
- Автотесты: **229 passed**
- `compileall`: PASS
- shell syntax: PASS
- Docker Compose YAML parse: PASS
- TS/TSX transpile: PASS
- ZIP integrity: PASS

## Найденные и исправленные проблемы

### CRITICAL-01 — отсутствие DB-инварианта для payment idempotency

**Проблема:** идемпотентность платежей ранее защищалась приложением/Redis, но не имела окончательного уникального инварианта в PostgreSQL. При race между двумя процессами оставалось окно для двух durable intents с одинаковым `(user_id, idempotency_key)`.

**Исправление:** добавлен `UNIQUE(user_id, idempotency_key)` на `payments` и migration `0031_v1_0_0_idempotency_integrity`.

Миграция сначала обнаруживает существующие дубли и **fail-closed** останавливается с перечислением конфликтующих ключей вместо молчаливого изменения финансовой истории.

### CRITICAL-02 — истечение Redis lease во время долгих внешних операций

Проверены все долгоживущие критические секции. Исправлены оставшиеся фиксированные leases:

- payment creation;
- fulfillment user lock;
- auto-renew per-attempt lock;
- backup lock;
- restore/maintenance lock.

Теперь они используют общий token-bound renewal механизм. Renew выполняется только если Redis-ключ всё ещё принадлежит исходному token, поэтому старый владелец не может продлить уже захваченный другим процессом lock.

### IMPORTANT-01 — race при параллельной регистрации Telegram/Yandex

При двух одновременных первых логинах один и тот же identity мог пройти отсутствие записи одновременно в двух транзакциях и упереться только в unique constraint.

Добавлена PostgreSQL transaction advisory serialization по стабильному хэшу identity перед созданием пользователя.

Для Yandex также введена проверка обязательного стабильного identifier.

### IMPORTANT-02 — race при lazy bootstrap payment-provider health

Health-записи платёжных провайдеров создавались лениво. Несколько первых запросов могли одновременно попытаться создать одну и ту же unique-запись.

Добавлена transaction advisory serialization вокруг bootstrap.

### IMPORTANT-03 — race при bootstrap первого admin

Параллельный startup нескольких API replicas мог одновременно увидеть отсутствие bootstrap-admin.

Добавлена transaction advisory serialization перед проверкой/созданием bootstrap-admin.

## Повторно проверенные зоны

- authentication / session lifecycle / CSRF;
- Telegram initData и Yandex OAuth;
- RBAC и административные permissions;
- payment creation, provider binding и idempotency;
- webhook provider/order binding;
- refund state machine;
- fulfillment и Remnawave provisioning;
- auto-renew;
- trial grants;
- referral rewards и withdrawals;
- device limits;
- account deletion/privacy;
- Redis distributed locks и lease ownership;
- backup/restore;
- upload limits и archive traversal;
- monitoring URL validation и DNS pinning;
- Alembic migration chain;
- release tooling;
- frontend TS/TSX syntax/transpilation.

## Безопасность миграции

Migration `0031` не удаляет и не выбирает произвольно одну из конфликтующих payment-записей. Если в production БД уже существуют дубли `(user_id, idempotency_key)`, миграция намеренно останавливается и требует финансовой сверки.

## Что не заявляется как выполненное

- live production payment E2E с реальными merchant credentials;
- live Remnawave provisioning против production Panel;
- полноценный production restore с реальной инфраструктурой;
- dependency audit через `pip-audit` — утилита отсутствовала в окружении;
- полноценный Vite production build без установленных frontend dependencies.

При этом синтаксическая/transpile-проверка TS/TSX выполнена.

## Методика

Аудит ориентирован не только на сигнатурные уязвимости, но и на бизнес-логику, state transitions, transaction integrity, TOCTOU/race conditions, идемпотентность и конкурентный доступ к общему состоянию. Такой подход соответствует рекомендациям OWASP по baseline secure code review и business-logic review.
