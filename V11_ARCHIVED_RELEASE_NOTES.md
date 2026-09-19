# Release 12 — Security, optional 2FA and full-project backups

## Changes
- TOTP 2FA is now **OFF by default** and is enabled/disabled from the Admin panel.
- Enabling TOTP requires scanning the secret and confirming a live 6-digit code.
- Disabling TOTP requires the administrator password and is audited.
- Admin JWTs enforce MFA only when the account has MFA enabled.
- Added Backup Center in Admin: schedule, retention, encryption password, include `.env`, manual backup, history, download and automatic retention cleanup.
- Backups contain project source/config, PostgreSQL dump and persistent media. Backup archives are encrypted by default.
- Added backup job database tracking and scheduler.
- Added PostgreSQL client/OpenSSL to backend image for backup creation.
- Fixed Remnawave subscription/user ID handling: UUID/string identifiers are no longer cast to `int`.
- API health reports release `11.0`.

## Security notes
- If `.env` is included, encryption is mandatory.
- Backup encryption password is stored encrypted with `APP_SECRET`; it is never returned by the API.
- The backup directory is not included recursively in backups.
- The Admin download endpoint requires an authenticated admin session.
