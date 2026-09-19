# Release Notes — 1.0.4-realise

## Security / Critical Fix

- Унифицирован порядок distributed locks для fulfillment и auto-renew: `user → payment`.
- Устранён конфликт lock acquisition, способный оставить подтверждённый платёж без своевременного provisioning.
- `fulfill()` больше не освобождает user lock, которым владеет вызывающий auto-renew workflow.
- Сохранён token-safe Redis renewal/release lifecycle.

## Verification

- 242 tests passed.
- Python compileall passed.
- Shell syntax passed.
- Docker Compose YAML parse passed.
- ZIP integrity passed.
- SHA-256 verification passed.

## Database

No new migration. Head: `0031_v1_0_0_idempotency_integrity`.

## Documentation

В релиз включены существующие project documentation files, operational runbooks, API references, production checklists, security model и предыдущие audit reports. Новый критический audit report: `V1_0_4_CRITICAL_AUDIT_RU.md`.
