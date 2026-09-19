# V22 Production Release

V22 closes the remaining P0-P2 issues identified in V21:
- recurring payment confirmation before provisioning;
- restore maintenance lock, session isolation and Alembic migration after restore;
- backup archive bomb/path/link/size limits;
- atomic webhook deduplication;
- fulfillment distributed locking, retry cap and terminal state;
- auto-renew lifecycle/failure handling;
- S3 installer configuration and production metrics token generation;
- V22 installer/version labels;
- safer proxy header trust.

Validation in this build is static/compile/archive based. Docker daemon, npm registry and real payment/Remnawave sandbox credentials were unavailable in the build environment, so those live integrations must still be exercised on a staging VPS.
