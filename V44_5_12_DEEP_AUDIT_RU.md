# V44.5.12 — очень глубокий аудит и исправления

## Область проверки

Проверены backend/API, PostgreSQL-модели и миграции, платежи и webhook-контур, durable payment intents, reconciliation/retry, fulfillment и Remnawave provisioning, trial, promo/referral, устройства, MFA/admin sessions, backup/restore, monitoring/SSRF guardrails, Docker/Compose и release tooling.

Отдельно проверялись бизнес-инварианты, state transitions, TOCTOU/race conditions и идемпотентность внешних side effects. Для финансовых операций принципиально запрещено полагаться только на UI или happy-path.

## Новые исправления V44.5.12

### HIGH — trial можно было получить при действующей подписке

`/api/me/trial` не проверял наличие активной локальной подписки. Пользователь с оплаченной VPN-подпиской мог дополнительно получить бесплатный trial и продлить entitlement.

Исправлено: активная подписка блокирует trial; проверка выполняется под row lock.

### HIGH — unknown payment не всегда мог быть привязан к webhook

Для durable payment intent `provider_payment_id` до ответа провайдера равен NULL. Если провайдер принял платёж, но HTTP-ответ потерялся, webhook содержит provider payment ID, однако старый lookup искал только по этому ID и не находил локальный Payment.

Исправлено: webhook может безопасно найти intent по immutable `order_id`/provider metadata, проверить сумму/валюту через provider API и только после проверки привязать provider ID.

Поддержано для YooKassa, Platega и RollyPay там, где webhook передаёт order/payload.

### HIGH — существующий remote user при recovery мог сохранить старые entitlement

Recovery ветка fulfillment могла найти пользователя Remnawave по username, но не переактивировать disabled user и не применить snapshot оплаченного тарифа.

Исправлено: recovery теперь повторно включает disabled/blocked/inactive user и применяет traffic/profile snapshot.

### MEDIUM — downgrade до unlimited/no-profile не очищал старые Remnawave значения

`update_entitlements()` обновлял remote quota/profile только когда значение было задано. Поэтому переход на тариф без traffic limit/profile мог оставить старое ограничение или старый internal squad.

Исправлено: `None` теперь означает явное очищение: `trafficLimitBytes=0`, `activeInternalSquads=[]`, согласованно с create-user semantics.

### MEDIUM — fallback event ID webhook был неуникальным

Для YooKassa отсутствие event ID могло использовать строку события (`payment.succeeded`) как fallback, что создавало общий идентификатор для разных webhook.

Исправлено: fallback всегда является SHA-256 исходного payload.

### DB hardening

Добавлена миграция `0028_v44_5_12_logic_integrity` с CHECK constraints для:

- допустимого диапазона trial days;
- неотрицательных promo counters;
- положительной суммы Payment;
- неотрицательной скидки.

## Проверки

- 194 теста — PASS
- Python compileall — PASS
- AST parsing — PASS
- Bash syntax — PASS
- Docker Compose YAML — PASS
- migration chain — PASS
- единственная migration head: `0028_v44_5_12_logic_integrity`
- dangerous-pattern scan (`shell=True`, `verify=False`, `pickle.loads`, небезопасный `yaml.load`) — PASS
- release build — PASS
- ZIP integrity — PASS
- SHA-256 manifest — PASS

## Ограничения

В sandbox отсутствуют реальные production/staging credentials платёжных провайдеров, live Remnawave API и production Docker runtime. Поэтому настоящий внешний E2E не объявляется пройденным. Локальные regression/static/build проверки выполнены на финальном состоянии проекта.
