# V23 Production — Reliability & Recovery

V23 hardens the V22 release around the remaining P0/P1 failure modes.

## Fixed
- Persistent provisioning operation per payment; stable Remnawave username recovery after lost create responses.
- Per-payment and per-user fulfillment locks.
- Webhook verification now happens before event consumption; provider events have lifecycle fields.
- Backup tar validation rejects absolute paths and `..` traversal and media extraction uses safe extraction.
- Restore stays in maintenance/recovery mode after a failed restore instead of silently clearing the flag.
- Payment idempotency fingerprint includes provider.
- `plan_id` input validation no longer turns malformed input into a 500.
- Sensitive connection information is `no-store`.
- Metrics fail closed when enabled without a token.
- Worker heartbeat and Recovery Center API.
- Incident mode and referral ledger reconciliation endpoint.
- Update creates a rollback snapshot; standalone rollback script added.
- PyJWT pinned.
- Removed duplicate metrics configuration and stale V21 UI labels.
- Removed `.pytest_cache` from release artifacts.

## Important operational note
V23 still requires a real Docker/PostgreSQL/Redis/Remnawave/payment-provider integration test before a live production rollout. This environment cannot provide those external services, so the release does not claim live integration verification.
