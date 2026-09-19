# V32.0.0 Production — Operations, Security & Reliability

## One-step installation

```bash
sudo bash install.sh
```

The installer generates `.env`, creates frontend lockfiles, pins runtime and build-stage images by digest, configures firewall/Fail2Ban, builds and starts the stack, runs health checks and prints the resulting URLs and credentials. No manual configuration-file editing is required.

## P0/P1/P2 fixes

- Fixed S3-disabled configuration to write a real boolean (`false`) instead of an empty value.
- Added a safe `.env.example` and removed stale V30 release metadata.
- Release version, migration head and frontend labels are now V32.
- Build-stage Python/Node/Nginx images can be pinned by digest by the installer.
- Withdrawal operations use dedicated RBAC permissions instead of `analytics.read`.
- Manual `mark-refunded` is disabled; refunds must go through provider execution/reconciliation.
- Added provider refund-status reconciliation hooks and scheduler.
- Added `Decimal` money contracts where required.
- Added persistent incident maintenance-state restoration.
- Added structured operational job records for fulfillment.

## New functions

### Monitoring Center
- disk usage
- request/error metrics
- worker fleet health
- stale worker detection
- job queue counts

### Job Queue
- durable jobs
- attempts/max attempts
- retry timestamps
- worker ownership
- failure messages
- admin retry endpoint

### Anti-Fraud
- payment velocity signals
- fulfillment failure velocity signals
- signal scoring/status
- admin review/resolve/block endpoint
- manual scan endpoint

### Payment reconciliation
- existing payment reconciliation retained
- refund reconciliation scheduler
- provider-specific `get_refund_status` adapter hooks
- failed/cancelled/succeeded refund state handling

### Referral payouts
- dedicated payout transaction records
- approval and paid lifecycle
- payout history endpoint
- separate withdrawal permissions

### Customer privacy
- data export endpoint
- safe account anonymization endpoint
- deletion blocked while an active subscription exists

### Traffic dashboard
- Remnawave traffic usage
- traffic limit
- device count
- status and expiration

### Incident Center
- preserves previous maintenance state
- restores it when incident mode is disabled

## Validation

- 60/60 tests pass.
- Python compilation passes.
- Shell syntax validation passes.
- Docker Compose YAML parsing passes.
- Live Docker/provider/Remnawave E2E still requires a real staging VDS and provider sandboxes.

## Release signing

The archive is intentionally not self-signed. Generate the detached manifest after calculating the archive SHA256 and sign the manifest with the operator private key. Verify with `scripts/verify-release.sh` before production activation.
