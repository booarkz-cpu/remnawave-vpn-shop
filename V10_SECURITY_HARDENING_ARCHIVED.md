# V10 Security Hardening

- Admin authentication: password + TOTP, with mandatory first-login enrollment.
- Admin setup tokens are explicitly typed (`mfa_setup`) and cannot be used as admin API tokens.
- Login brute-force limiter: 8 failed attempts per IP/email key in 15 minutes.
- Passwords: scrypt with per-password random salt.
- Admin API: MFA-verified JWT + RBAC.
- PostgreSQL and backend are not published to the host.
- Docker services use `no-new-privileges`; application containers drop Linux capabilities and use read-only filesystems where compatible.
- HTTPS security headers are emitted by Caddy and API.
- Uploads are restricted by MIME type and 5 MiB size for admin images.
- API documentation/OpenAPI is disabled in production.
- Telegram WebApp initData expires after 10 minutes.
- Yandex OAuth state is signed and bound to a secure, HTTP-only cookie; user JWT is returned in URL fragment.
- Audit log is available in the admin panel.
