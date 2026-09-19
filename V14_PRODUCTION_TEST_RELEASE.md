# V15 Production Test

## Release

`15.0.0-production`

V14 is a security and reliability hardening release over V12.

## Fixed

- User and admin authentication moved to Secure/HttpOnly cookies; Bearer remains accepted for backwards-compatible automation.
- Double-submit CSRF protection for cookie-authenticated state-changing requests.
- Yandex OAuth now returns a one-time 60-second exchange code instead of a JWT in the URL fragment.
- Redis-backed distributed rate limiting.
- Atomic broadcast claiming with PostgreSQL `FOR UPDATE SKIP LOCKED`.
- Broadcast audience: `all`, `active`, `inactive`.
- Promo usage is no longer incremented when a payment is merely created; it is consumed during successful fulfillment under row lock.
- Promotion priority is stored and used for deterministic selection.
- HTTPS-only validation for externally navigated content URLs.
- Telegram HTML content is escaped before sending CMS-controlled text.
- YooKassa webhook IP allowlist is enforced.
- Platega webhook now re-checks transaction status, amount and currency via the provider API.
- RollyPay webhook now re-checks payment status, amount and currency via the provider API and checks `order_id`.
- Admin management endpoints and UI.
- MFA recovery codes.
- Redis distributed backup lock.
- CORS explicitly permits `X-CSRF-Token`.
- Content/Mini App/marketing/admin sections were added to the web panel.
- Redis is part of the Docker stack and is health-checked.
- Content Security Policy added at Caddy.

## Database

Alembic head:

`0006_v14_security`

Migration adds:

- `auth_exchange_codes`
- `admin_users.recovery_codes_encrypted`
- `promotions.priority`
- `promotions.exclusive`

## Test results in the build environment

Passed:

- Python AST parse for backend sources.
- Python bytecode compilation (`py_compile`).
- Shell syntax checks for deployment/update/backup scripts.
- Docker Compose YAML parse.
- Alembic revision chain check; one head: `0006_v14_security`.
- 7 static V14 security/reliability contract tests.

Not executable in this environment:

- Docker daemon is not available, so an actual `docker compose build --pull --no-cache` cannot be honestly reported as executed.
- npm dependencies cannot be downloaded because outbound registry/DNS access is unavailable. Therefore the Vite production build must be performed on a connected VDS/CI runner.
- Real payment-provider, Telegram, Yandex and Remnawave E2E calls require real/staging credentials and external services.

## Required VDS production test

After deployment:

```bash
cd /opt/vpn-shop
docker compose config
docker compose build --pull --no-cache
docker compose up -d
docker compose ps
./scripts/doctor.sh
```

Then verify:

1. Admin login + MFA recovery code.
2. Yandex login; callback URL must end in `/api/auth/yandex/callback`.
3. Telegram Mini App login.
4. Create a test payment with every configured provider.
5. Confirm webhook amount/currency and fulfillment.
6. Create a promo with a one-use limit and perform two successful test payments concurrently; only one must receive the discount.
7. Start a broadcast and verify `all`, `active`, and `inactive` audiences.
8. Create/edit Bot/Mini App content from the admin panel.
9. Create and download an encrypted backup.
10. Restore the backup on a staging VDS before treating it as a disaster-recovery copy.
