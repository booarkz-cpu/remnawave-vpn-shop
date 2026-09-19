# V30 Final Hardening Release

V30 is the post-V28 corrective release. It fixes the remaining production audit findings rather than adding speculative features.

## Payment providers
- Platega and RollyPay refunds no longer call YooKassa.
- Provider-specific refund endpoints are explicit configuration (`PLATEGA_REFUND_URL`, `ROLLYPAY_REFUND_URL`). If absent, the system refuses the operation instead of sending a cross-provider request.
- Refund completion revokes the remote Remnawave user when possible and exposes a recovery endpoint when revocation fails.

## Provisioning
- Extension operations persist expected remote expiry timestamps.
- After an external timeout, retry reconciles the remote expiry before issuing another extension, preventing double-extension.
- Existing payment/user Redis locks remain in place.

## Referral withdrawals
- Balance deduction is atomic at the SQL level.
- Rejected withdrawals restore the balance and write a compensating ledger entry.

## Auto-renew
- Per-user/date distributed lock prevents concurrent renewal attempts.
- Existing pending recurring payments are reconciled before a new charge is created.

## Recovery and updates
- Update/rollback filesystem snapshots exclude `.env` and `.env.*` secrets.
- Update snapshots include a PostgreSQL dump and rollback restores both application files and DB when possible.
- Backup downloads use `Cache-Control: private, no-store`.
- Integration smoke test publishes backend only on the integration port 18000.

## Security
- Security Center uses the actual `BOT_TOKEN` and `REMNAWAVE_TOKEN` settings.
- V30 migration adds provisioning expiry reconciliation fields.

## Validation
- Python syntax/compile: PASS
- Shell syntax: PASS
- Static regression suite: PASS
- Full live Docker/payment/Remnawave tests still require a real staging environment.
