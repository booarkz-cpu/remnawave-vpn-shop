# Release Notes — V1.0.9-realise

## Критические исправления

- Исправлен `NameError` в `_confirm_and_fulfill_payment()`, блокировавший atomic payment confirmation workflow.
- Fulfillment теперь повторно читает User через `SELECT ... FOR UPDATE` даже при переданном существующем user-lock token.
- Закрыт stale-ORM/TOCTOU путь между account deletion и Remnawave provisioning в auto-renew и других вызывающих путях.
- Добавлены V1.0.9 regression tests.

## Совместимость

- Новая DB migration не требуется.
- Migration head остаётся `0031_v1_0_0_idempotency_integrity`.
- Предыдущий релиз: `1.0.8-realise`.
