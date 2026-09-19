# V14 Security Notes

- The Mini App no longer stores user JWTs in `localStorage`.
- The Admin UI no longer stores admin JWTs in `localStorage`.
- Cookies are `Secure`, `HttpOnly` for auth, and `SameSite=None` for cross-subdomain API usage.
- CSRF token is a separate non-HttpOnly cookie and must be sent as `X-CSRF-Token` on state-changing requests.
- Yandex callback exposes only a one-time short-lived exchange code.
- Redis is mandatory for the production backend startup and is internal-only in Docker Compose.
- Public content links are restricted to absolute HTTPS URLs.
- Payment webhooks must validate both authenticity and the provider-side payment amount/currency before fulfillment.
- Backups remain local to the VDS. A true disaster-recovery setup should copy encrypted backups to an external S3-compatible/object-storage destination and periodically test restores.
