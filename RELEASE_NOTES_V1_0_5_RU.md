# Release Notes — 1.0.5-realise

## Critical fix

Исправлен stale-state race между fulfillment и refund/reconciliation: fulfillment теперь повторно блокирует и проверяет Payment непосредственно после получения общего payment lock, до любого Remnawave side effect.

## Verification

245 тестов PASS; compileall, shell syntax, Compose YAML и ZIP integrity PASS.

Новая migration не требуется; head остаётся `0031_v1_0_0_idempotency_integrity`.
