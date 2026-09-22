# V42 Production Checklist

## Before deployment
- [ ] Generate a unique APP_SECRET (>=32 chars).
- [ ] Set DB_PASSWORD and all provider credentials.
- [ ] Set API_DOMAIN, ADMIN_DOMAIN, APP_DOMAIN and CABINET_DOMAIN.
- [ ] Configure strict firewall: SSH + TCP 80/443 + UDP 443 only.
- [ ] Configure S3/R2/B2 if off-site backups are required.
- [ ] Configure Telegram/SMTP alerts.
- [ ] Run `scripts/preflight.sh`.
- [ ] Run `scripts/security-scan.sh`.
- [ ] Run `scripts/integration-test.sh` on a Docker-enabled staging host.

## First boot
- [ ] `docker compose config` passes.
- [ ] `docker compose up -d` passes.
- [ ] `scripts/doctor.sh` reports API health OK.
- [ ] Worker heartbeat is visible in Recovery Center.
- [ ] Admin enables 2FA from Security; it is not forced before setup.
- [ ] Create and verify a backup.
- [ ] Validate and test-restore a backup in staging.

## Payment smoke test
- [ ] Create one test payment.
- [ ] Confirm provider status and webhook.
- [ ] Confirm exactly one provisioning operation is created.
- [ ] Confirm Remnawave user/subscription exists.
- [ ] Replay the webhook; no duplicate provisioning occurs.
- [ ] Force a timeout/retry in staging; reconciliation completes the original operation.
- [ ] Test refund request/review/confirmation flow.

## Security
- [ ] Never expose PostgreSQL/Redis/backend ports publicly.
- [ ] Keep APP_SECRET_PREVIOUS only during a controlled rotation window.
- [ ] Rotate metrics token periodically.
- [ ] Review audit logs and admin sessions.
- [ ] Verify backups are encrypted when `.env` is included.
- [ ] Review disk usage and certificate expiry.

## Update / rollback
- [ ] Run `scripts/update.sh`.
- [ ] Confirm pre-update snapshot exists.
- [ ] Confirm migration + health checks pass.
- [ ] If health fails, run `scripts/rollback.sh` and re-check health.
