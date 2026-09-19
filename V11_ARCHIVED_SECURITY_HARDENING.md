# V11 Security Hardening

- 2FA/TOTP is optional and is controlled in Admin → Security.
- When MFA is enabled for an account, admin JWTs without a valid MFA verification are rejected.
- TOTP secret is encrypted at rest with a key derived from APP_SECRET.
- MFA disable requires the current admin password and is audited.
- Admin login is rate-limited by IP + email.
- Full-project backups are created inside the backend without Docker socket access.
- Backup archives can contain source/config, PostgreSQL dump and media.
- Including `.env` requires encryption.
- Backup encryption password is encrypted at rest and never returned by the API.
- Backup download requires an authenticated admin with the `admin` role.
- PostgreSQL and backend ports remain internal to Docker.
- Backend runs without extra Linux capabilities and with a read-only root filesystem.
- Project source is mounted read-only only for backup creation; no Docker socket is exposed.
