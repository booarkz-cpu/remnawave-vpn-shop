# Release Notes — V1.0.6-realise

## Critical fix

Исправлен критический конфликт порядка distributed locks между fulfillment и refund/reconciliation.

### До

Refund paths могли удерживать `payment lock`, а затем переходить к user/subscription state. Fulfillment использовал обратный порядок `user -> payment`.

### После

Все финансовые side-effect paths используют единый порядок:

`user -> payment -> DB state -> external side effect`

После получения locks `Payment` и `RefundRequest` перечитываются с `FOR UPDATE`.

## Regression coverage

Добавлены проверки:

- единый lock order для всех refund entry points;
- повторная проверка Payment/RefundRequest после обоих locks.

## Verification

247 tests passed. Compile, shell syntax, Compose parsing и archive integrity проверены.
