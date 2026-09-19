# Security Model V43

## Границы доверия

Browser/Telegram → Caddy → Backend → PostgreSQL/Redis/Remnawave/Payment Providers.

## Основные меры

- Trusted Host.
- CORS allowlist.
- CSRF для cookie-auth mutations.
- HttpOnly auth cookies.
- Rate limits.
- Admin idle/absolute session timeout.
- User-Agent session binding.
- RBAC.
- MFA/TOTP.
- Audit Log.
- Step-up security для критических действий.
- Provider webhook verification.
- Payment amount/currency verification.
- Durable jobs и locks.
- Idempotency.
- Fail-closed production gate.
- Encrypted secrets.
- Safe archive extraction.
- Isolated backup restore.
- Loopback-only staging runner endpoint.

## Content security

User/admin supplied links are validated as HTTPS URLs. Uploaded images are constrained by MIME, file signature and size. Admin content APIs do not expose raw secret settings.

## Production Gate

Gate нельзя считать доказательством безопасности сам по себе. Он лишь разрешает production payment creation после внешнего E2E подтверждения.
