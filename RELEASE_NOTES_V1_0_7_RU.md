# Release Notes — V1.0.7-realise

## Critical fix

Закрыта race condition в fulfillment: stale `User` snapshot после получения user-level distributed lock больше не может привести к provisioning удалённого аккаунта.

## Compatibility

Новая DB migration не требуется. Migration head: `0031_v1_0_0_idempotency_integrity`.

## Verification

249 тестов PASS. Остальная доступная документация предыдущего релиза сохранена в полном архиве.
