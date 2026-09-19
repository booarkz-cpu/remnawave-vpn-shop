# API / Operations

## Authentication
Admin and user sessions use secure HttpOnly cookies plus CSRF tokens. Mutating browser requests require `X-CSRF-Token`.

## Payments
`POST /api/payments/create` requires `Idempotency-Key`. A payment is fulfilled only after the provider confirms the exact amount/currency and a `paid` state is recorded.

## Webhooks
Provider events are deduplicated by a database unique constraint using atomic `ON CONFLICT DO NOTHING`.

## Backups
Backups support SHA-256 verification, optional encryption and S3-compatible off-site storage. Restore requires confirmation and admin MFA when MFA is enabled, enters maintenance mode, creates a pre-restore backup, restores the database, runs `alembic upgrade head`, and checks database health before leaving maintenance mode.

## Fulfillment
Failed fulfillment retries exponentially up to `FULFILLMENT_MAX_ATTEMPTS` (default 8). Terminal failures require manual resolution. A Redis distributed lock prevents duplicate fulfillment.

## Auto-renew
Recurring charges remain `pending` until provider verification returns `succeeded` with matching amount/currency. Repeated failures move the method to `payment_failed` and disable auto-renew.

## Metrics
`/metrics` should be protected by `METRICS_TOKEN` in production.


## V40 API

Authenticated administrators can retrieve the generated OpenAPI schema from `/api/admin/openapi.json`. The public interactive Swagger UI remains disabled in production to reduce attack surface.

New V24–V28 endpoints include:
- `/api/me/dashboard`
- `/api/me/support/tickets`
- `/api/me/referral/withdrawals`
- `/api/admin/recovery/operations`
- `/api/admin/refunds`
- `/api/admin/refunds/{refund_id}/execute`
- `/api/admin/support/tickets`
- `/api/admin/referrals/withdrawals`
- `/api/admin/workers`
- `/api/admin/releases`
- `/api/admin/security/secrets/status`
- `/api/admin/security/incidents`
- `/api/admin/openapi.json`
