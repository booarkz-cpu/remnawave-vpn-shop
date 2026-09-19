# V15.0.0 Production Release

## Critical fixes
- Fixed backend import-time `NameError` in `LoginIn`.
- Fixed menu deletion `NameError` and added audit event.
- Admin Remnawave connection keys now require `manage_users`.
- MFA setup/enable/disable now require `manage_own_mfa`; MFA login locks the admin row during recovery-code consumption.
- Added backup SHA-256 checksum and encrypted flag with Alembic migration.
- Added server-side pagination to admin payments and audit logs.
- Strict firewall documentation and installer output aligned with actual UFW policy.

## Hardening
- Strict firewall is the default configuration.
- Backup metadata exposes checksum/encryption state for integrity verification.
- Production test suite updated to detect the V14 runtime regressions.

## Validation
- Python source compilation: PASS.
- V15 static regression suite: PASS.
- Full Docker integration requires a target host with Docker and configured `.env`; release scripts perform Compose validation and backend health checks.
