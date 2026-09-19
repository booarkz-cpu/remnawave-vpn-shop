# V24–V28 Production Release

V28 is the consolidated production release containing the V24 Reliability, V25 Security, V26 Customer, V27 Business and V28 Operations workstreams.

## V24 Reliability
- two-way payment reconciliation for pending and paid-but-unfulfilled payments;
- persistent provisioning operations with retry/recovery state;
- per-payment and per-user fulfillment locks;
- webhook provider-scoped idempotency;
- safe backup/restore path validation and persistent restore failure state;
- refund request lifecycle with explicit administrative confirmation;
- integration compose profile and end-to-end smoke-test script.

## V25 Security
- dual-key APP_SECRET rotation support through APP_SECRET_PREVIOUS;
- encrypted secret decryption during controlled key rotation;
- session invalidation remains available through the existing revoke-all flow;
- Security Center secret configuration status without exposing secret values;
- worker state/heartbeat persistence;
- Docker no-new-privileges/capability dropping/read-only hardening retained;
- connection and dashboard responses use no-store caching.

## V26 Customer
- full customer dashboard API;
- support tickets and admin replies;
- subscription/payment/referral visibility;
- connection QR and subscription URL access;
- Mini App redesigned around account, subscription, payments, referrals and support.

## V27 Business
- referral withdrawal requests;
- admin withdrawal approval/payment lifecycle;
- refund center;
- payment lifecycle states remain auditable;
- referral ledger reconciliation remains available.

## V28 Operations
- worker fleet dashboard;
- release history/check endpoint;
- update/rollback scripts with snapshots and health checks;
- CI workflow for compile, tests, shell checks and Compose validation;
- integration test profile;
- Caddy configuration validation healthcheck;
- release documentation and production checklist updates.

## Validation
- Python compile: passed.
- Shell syntax: passed.
- Automated test suite: 35 passed.
- Docker runtime/live integration: not executed in this build environment because no Docker daemon is available.
- Frontend npm build: not executed because the environment has no dependency registry/cache sufficient to install the frontend dependency tree; lockfiles were not fabricated.

## Container reproducibility
- runtime base images use fixed version tags;
- `scripts/pin-images.sh` resolves the runtime image tags to immutable RepoDigests on the target host and stores them in `.env.images`;
- `deploy/build-production.sh` consumes `.env.images` when present.
