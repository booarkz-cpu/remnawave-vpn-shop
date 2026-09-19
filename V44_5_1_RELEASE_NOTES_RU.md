# Remnawave VPN Shop 44.5.1 Enterprise — глубокий аудит и исправления

Дата: 2026-09-14

## Исправления

### CRITICAL / HIGH — платёжная маршрутизация

Исправлена ошибка в `_payment_provider_order`: поле `PaymentProviderHealth.enabled` фактически не участвовало в выборе провайдера.

До исправления администратор мог отключить провайдера в панели, но checkout продолжал выбирать его.

Дополнительно routing теперь отбрасывает провайдера без обязательных credentials для создания платежа. Это переводит ошибку из позднего момента после начала checkout в безопасный fail-closed на этапе выбора провайдера.

Проверяются:
- ЮKassa: `shop_id` + `secret_key`;
- Platega: `merchant_id` + `secret`;
- RollyPay: `api_key`.

Circuit breaker по-прежнему учитывается.

### Release consistency

Версия повышена до `44.5.2-enterprise` и синхронизирована с:
- application version;
- build-release script;
- VPS installer;
- release manifest template;
- regression contract tests.

## Аудит

Проведены проверки:
- весь backend Python AST/compileall;
- Bash syntax всех release/ops scripts;
- Docker Compose YAML;
- миграционная цепочка Alembic;
- платёжные webhook handlers;
- idempotency и duplicate webhook paths;
- fulfillment locking и retry;
- Remnawave expiry monotonicity;
- MFA/session/RBAC/CSRF;
- backup restore/archive traversal;
- SSRF validation;
- frontend URL handling/XSS surface;
- referral balance atomicity;
- trial/device concurrency;
- production payment gate.

## Тесты

`pytest`: **121 passed**.

Также:
- `compileall`: OK
- `bash -n`: OK
- Docker Compose YAML parse: OK

## Ограничения

Реальные внешние sandbox credentials платёжных систем, Docker daemon и production Remnawave environment отсутствуют в среде аудита. Поэтому внешний provider E2E не выдаётся за успешно пройденный. Production payments должны оставаться заблокированными до реального staging E2E.
