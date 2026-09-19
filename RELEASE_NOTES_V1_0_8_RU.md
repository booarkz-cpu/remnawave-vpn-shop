# Release Notes — V1.0.8-realise

## Security / critical fixes

- Устранено stale-success race: webhook/reconciliation больше не может воскресить `refunded` Payment в `paid`.
- Все provider-success confirmation paths используют единый lock-aware helper.
- Добавлена повторная `SELECT ... FOR UPDATE` проверка перед финансовым state transition.
- Сохранён единый порядок locks: `user → payment`.
- Добавлены critical regression tests.

## Verification

- 252 tests passed.
- compileall, shell syntax, Compose YAML и release integrity checks passed.
- Migration head: `0031_v1_0_0_idempotency_integrity`.
