# V10 — Security + Admin Control Center

## Security hardening
- Mandatory TOTP enrollment on first admin login.
- MFA setup token has a dedicated `type=mfa_setup` claim and cannot access admin endpoints.
- Admin API accepts only MFA-verified admin tokens.
- Admin login brute-force limiter: 8 failures per IP/email key per 15 minutes.
- Fail2Ban SSH jail enabled by installer (5 failures / 10 min, 1 hour ban).
- Unattended security updates enabled where supported.
- Security headers on API, Admin and Mini App virtual hosts.
- HSTS enabled on HTTPS hosts.
- OpenAPI/Swagger/ReDoc disabled in production.
- Backend and PostgreSQL remain internal Docker services.
- Application containers use no-new-privileges, dropped Linux capabilities and read-only root filesystems where compatible.
- Admin image uploads restricted to PNG/JPEG/WebP/GIF and 5 MiB.
- Telegram Mini App initData lifetime: 10 minutes.
- Yandex OAuth state is signed and protected by an HTTP-only secure cookie; user JWT is returned in URL fragment.

## Admin Control Center
- Redesigned dark production dashboard.
- System status cards, user/payment/node metrics and security state.
- Responsive sidebar navigation.
- Dedicated Security Center.
- Dedicated Audit view.
- First-login 2FA enrollment flow.
- Plan management and core operational views.
