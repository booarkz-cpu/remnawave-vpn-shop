# V33.0.0 Production — Reliability & Release Hardening

- Durable Job Queue worker added with PostgreSQL SKIP LOCKED, leases and dead-worker recovery.
- Refund reconciliation now calls the configured provider adapter and persists verified status.
- Refund execution rejects provider responses without a refund ID.
- Admin/Mini App release labels updated to V33.
- Fixed Admin/Compose restart policy placement.
- Added safe `.env.example`; installer remains one-step and generates production secrets.
- Worker failures now use structured logging instead of silent suppression in critical loops.
- Release manifest is detached and must contain the final archive SHA256; unsigned releases are explicitly marked unsigned.

Live Docker/Remnawave/payment-provider E2E still requires a real staging environment.


## One-step installer

`sudo bash install.sh` collects only infrastructure/provider values and writes `.env` automatically. It explicitly writes `BACKUP_S3_ENABLED=false` when S3 is disabled, pins runtime/build images, generates frontend lockfiles when the npm registry is available, applies migrations, starts the stack, and performs health checks.

## Job queue

The worker claims queued jobs with PostgreSQL row locking, leases processing jobs, recovers stale jobs after 10 minutes, executes supported fulfillment jobs, records attempts/errors and schedules bounded retries.
