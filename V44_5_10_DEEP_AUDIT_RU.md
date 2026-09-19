# Remnawave VPN Shop 44.5.10 Enterprise — Very Deep Systems Audit

## Scope

Повторно проверены все доступные подсистемы проекта: API/backend, PostgreSQL/Alembic, Redis locks, платежи и webhooks, fulfillment/Remnawave provisioning, auto-renew, trial, promo/referral, withdrawals, admin authentication/MFA/RBAC, backups/restore, monitoring/SSRF boundary, Docker/Compose и release pipeline.

Основной фокус — денежные операции и state-machine: idempotency, TOCTOU/concurrency, durable intents, webhook deduplication, retry/reconciliation и сохранение entitlement. OWASP отдельно отмечает эти классы как бизнес-логические риски, которые обычные сканеры часто не находят. 

## Новые найденные дефекты и исправления

### CRITICAL — webhook event deduplication конфликтовал с реальной схемой БД

Приложение выполняло `ON CONFLICT (provider,event_id)`, но историческая миграция создавала глобальный UNIQUE только на `event_id`. В PostgreSQL такой conflict target не соответствует уникальному индексу и webhook transaction мог завершаться ошибкой.

Исправление: миграция `0027_v44_5_10_financial_integrity` заменяет глобальный UNIQUE на `(provider,event_id)`, а SQL claim теперь соответствует этому invariant.

### CRITICAL — orphan/duplicate charge window при auto-renew

Auto-renew сначала выполнял внешний charge, а Payment записывался после него. Crash/timeout между provider acceptance и DB commit мог оставить внешний charge без локального durable intent.

Исправление: Payment intent создаётся и commit-ится **до** внешнего charge. Для YooKassa retry использует тот же `order_id` как idempotency key. Если результат внешней операции неоднозначен, система не создаёт новый charge с новым ключом.

### HIGH — orphan charge window в обычном checkout

Та же архитектурная проблема существовала в интерактивном checkout: запись Payment создавалась только после provider call.

Исправление: создаётся durable Payment intent со статусом `creating` до внешнего вызова. После успеха в него записывается provider payment id. При неопределённом результате статус становится `creation_unknown`; автоматический fallback на другой provider запрещён.

Для YooKassa повтор того же idempotency order безопасен. Для Platega/RollyPay при неопределённом результате автоматическое повторное списание запрещено — требуется reconciliation.

### HIGH — idempotency retry зависел от текущего состояния provider routing

Повтор исходного idempotent запроса мог быть заблокирован, если администратор после первой попытки отключил provider.

Исправление: сначала ищется существующий Payment intent, и только затем выбирается provider для нового checkout.

## Regression protection

Добавлены тесты на:

- соответствие webhook conflict target database constraint;
- nullable provider payment id для durable intents;
- создание interactive Payment до внешнего provider call;
- блокировку fallback после ambiguous provider result;
- безопасный retry YooKassa с тем же order/idempotency key;
- durable auto-renew intent до charge;
- migration head consistency.

## Verification

- **182 теста — passed**
- Python compile/AST — PASS
- Bash syntax — PASS
- Docker Compose YAML parsing — PASS
- Alembic migration graph — PASS; единственный head: `0027_v44_5_10_financial_integrity`
- ZIP integrity — PASS после release build
- release version consistency — PASS
- SHA-256 detached manifest — generated after final ZIP

## Environment limitations

Не утверждается, что выполнены реальные production E2E с платёжными credentials, live Remnawave API и Docker runtime: эти внешние системы недоступны в sandbox. `npm run build` frontend/admin и miniapp не запускался, поскольку `node_modules` отсутствуют; зависимости не устанавливались в рамках аудита.

`pip-audit` в sandbox также недоступен.

Эти ограничения не маскируются как PASS.
