# V12 Security Hardening

V12 усиливает V11, но не делает систему «абсолютно защищённой».

### Network
- Installer использует строгий UFW: разрешены только SSH (22), HTTP (80), HTTPS (443/TCP) и HTTP/3 (443/UDP).
- Это намеренно ослабляет сетевой perimeter. Рекомендуемый безопасный режим после установки: deny incoming + SSH/80/443.

### Application
- Trusted Host middleware.
- Request size limit 12 MiB.
- Per-route rate limiting.
- Admin/auth responses marked `no-store`.
- Admin JWT содержит тип и MFA claim; RBAC сохраняется.
- MFA optional и управляется из панели.

### Payments
- User JWT проверяется перед созданием заказа.
- Idempotency-Key обязателен.
- Payment fulfillment блокирует payment и user rows перед внешними Remnawave operations.
- Webhooks требуют provider-side verification/signature where supported.
- Promo usage check uses row locking.

### Backups
- Full source/config + PostgreSQL dump + media.
- `.env` only when explicitly enabled.
- `.env` requires encryption.
- Backup password encrypted with APP_SECRET.
- Download/delete paths are constrained to the backup directory.
- Retention is enforced automatically.

### Host / containers
- PostgreSQL/backend are not published to the host.
- backend/bot use no-new-privileges, dropped capabilities, read-only root filesystem and tmpfs.
- SSH fail2ban and unattended security upgrades are enabled.
- Production API docs are disabled.

### Remaining operational risks
- `APP_SECRET` is the root of trust for admin JWT and encrypted stored secrets; losing it makes those secrets unrecoverable.
- Strict UFW rules limit inbound exposure to SSH, HTTP, HTTPS and HTTP/3; future host services remain blocked unless explicitly opened.
- Restore is intentionally not automated in V12; backups should be tested offline before relying on them.
