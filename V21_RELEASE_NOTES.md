# V21 Production — complete V20→V21 change log

## Release
- Version: `21.0.0-production`
- Release scope: V20 Production Hardening + V21 Scale & UX

## V20 — Production Hardening

### Reliability
- Added a dedicated worker service for scheduled background jobs.
- Removed background scheduler duplication from the API process.
- Added payment reconciliation for pending provider payments.
- Added an admin "Reconcile payments" operation.
- Added provider webhook event idempotency records.
- Added Redis-backed Remnawave circuit breaker to stop retry storms.
- Added explicit database + Redis health checks to `/health` and admin health.
- Added Prometheus-compatible `/metrics` counters.

### Payments
- Added provider event deduplication.
- Added Redis-backed distributed payment-creation lock to prevent duplicate external payment creation under concurrent requests.
- Provider amount verification uses `Decimal` precision.
- Added automatic recurring payment support for YooKassa when the provider returns a saved payment-method token.
- Saved payment-method tokens are encrypted at rest.
- Added auto-renew scheduler with idempotent order IDs.
- Added auto-renew status/removal endpoints.
- Auto-renew remains opt-in and is disabled globally unless `AUTO_RENEW_ENABLED=true`.

### Backups / DR
- Added remote S3-compatible upload verification with `HEAD` size check.
- Added remote retention cleanup.
- Added encrypted backup validation endpoint.
- Restore now requires valid MFA when MFA is enabled.
- Restore creates a fresh pre-restore backup first.
- Restore validates archive paths against traversal.
- Restore can restore media files safely.
- Backup verification hashes files in streaming chunks instead of loading them entirely into RAM.

### Security
- Added security alert delivery via Telegram and optional SMTP email.
- Added "revoke all sessions" with MFA step-up.
- Fixed admin session revocation when role/password/email/disabled state changes.
- Added image magic-byte validation to prevent MIME spoofing.
- Preserved strict firewall model: only TCP 80/443 and UDP 443 are public, plus SSH on the host.
- Added dependency/security scan helper.

### Operations
- Added health alert worker for failed fulfillment and stale backups.
- Added `scripts/preflight.sh`.
- Added `scripts/security-scan.sh`.

## V21 — Scale & UX

### Mini App
- Added dedicated connection-info API.
- Added QR code generation for subscription URL.
- Added platform-specific connection guidance for iOS, Android, Windows, macOS and Linux.
- Added auto-renew status UI.
- Added referral program summary UI.
- Added subscription URL copy action.
- Preserved Telegram WebApp authentication and HttpOnly-cookie model.

### Referral system
- Added a referral ledger in addition to aggregate balance/reward records.
- Added referral ledger API.
- Rewards remain idempotent per payment.

### Admin
- Admin branding updated to V21.
- Added payment reconciliation action.
- Added revoke-all sessions action.
- Added backup checksum validation action.
- Added S3/R2/B2-compatible backup configuration fields.
- Security center now shows active sessions, recent fulfillment failures and backup freshness.

### Database
- Added migration `0009_v20_v21`.
- Added `payment_provider_events`.
- Added `referral_ledger`.
- Added `auto_renew_methods`.

## Important provider limitation
Recurring payments are implemented as a provider capability. V21 fully supports the YooKassa saved-payment-method flow when YooKassa returns a saved payment method ID. Platega/RollyPay remain one-time providers until their official recurring-token API is configured and verified; V21 never stores card data.

## Compatibility
- Existing V15–V19 database migrations remain intact.
- V21 is an additive migration.
- Existing admin sessions are invalidated when their account security properties are changed.

## Verification performed
- Python AST parsing / compilation: PASS.
- Regression tests: PASS.
- Migration chain static validation: PASS.
- Docker Compose static validation: PASS where YAML parser is available.
- Frontend source was updated, but a real Vite build requires npm dependencies; the build could not be executed in the isolated environment because package downloads were unavailable.
- Docker runtime integration was not claimed because the environment has no Docker daemon.
