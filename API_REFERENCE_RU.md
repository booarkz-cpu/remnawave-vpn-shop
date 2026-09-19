# API Reference — V43

## Аутентификация

Пользовательские API используют защищённые cookie/session механизмы. Mutating cookie-auth requests требуют `X-CSRF-Token`.

Админские операции требуют активной admin session и соответствующего RBAC permission.

## Content / Branding

- `GET /api/public/config` — только публичная конфигурация.
- `GET /api/admin/content` — контент без raw secrets.
- `PUT /api/admin/settings/{key}` — только `app_name`, `bot_name`.
- `POST /api/admin/bot/start-image` — изображение `/start`.
- `DELETE /api/admin/bot/start-image`.
- `PUT /api/admin/miniapp/config` — Mini App title/buttons/settings.
- `POST /api/admin/miniapp/image`.
- `POST /api/admin/miniapp/background`.

## Mini App buttons

`url`: требует абсолютный HTTPS URL.

`plans`: прокручивает список тарифов.

`promo`: требует промокод, который сервер валидирует при оплате.

`field`: требует существующее включённое custom field.

Максимум 30 кнопок.

## Telegram Bot

Bot menu item types:

- `webapp` — HTTPS Web App;
- `url` — HTTPS URL;
- `field` — вывод настроенного поля.

Некорректные URL не отправляются пользователю.

## Payments

`POST /api/payments/create` требует `Idempotency-Key`.

Один ключ не должен приводить к созданию второго заказа при retry. При неоднозначной ошибке провайдера автоматический fallback запрещён; используется безопасная reconciliation стратегия.

Production gate должен быть включён (`payments.production_gate=1`) только после полного E2E.

## Staging E2E

- `GET /api/admin/staging-e2e/config`
- `PUT /api/admin/staging-e2e/config`
- `POST /api/admin/staging-e2e/run`
- `GET /api/admin/staging-e2e/status`

Внутренний payment endpoint доступен только loopback runner и требует отдельный runner token.

## Operations

- `/api/admin/v41/analytics`
- `/api/admin/v41/crm/users`
- `/api/admin/v41/providers`
- `/api/admin/v41/diagnostics`
- `/api/admin/v41/incidents`
- `/api/admin/v41/backups/verification`
- `/api/admin/v41/backups/{backup_id}/test-restore`
- `/api/admin/v41/features`
- `/api/admin/v41/passkeys`

## Security rule

Никогда не добавляйте endpoint, возвращающий весь `AppSetting`. Секретные значения должны возвращаться только в виде статуса наличия или использоваться server-side.

## V2.0.0 Product API

### User
- `GET /api/me/billing-center` — billing center.
- `GET /api/me/security-center` — user sessions/devices/security events.
- `POST /api/me/security/revoke-all` — revoke all user sessions.
- `POST /api/me/subscription/lifecycle` — `cancel` / `resume` subscription.
- `POST /api/me/gifts/redeem` — redeem a gift code.

### Admin
- `GET /api/admin/customers/{user_id}/360` — Customer 360.
- `GET /api/admin/refunds/{refund_id}/dry-run` — refund simulation without mutation.
- `GET /api/admin/security/risk-summary` — fraud/risk summary.
- `GET /api/admin/health/summary` — PostgreSQL/Redis/Remnawave health.
- `GET /api/admin/gifts` — gift codes.
- `POST /api/admin/gifts` — create gift code.

## Финансовый журнал 2.1.0

- `GET /api/admin/financial-ledger` — последние 500 неизменяемых финансовых операций. Доступен администраторам с правом `payments.read`.
- `GET /health/live` — liveness.
- `GET /health/ready` — readiness; возвращает 503, если PostgreSQL или Redis недоступны.
- Заголовок `X-Request-ID` возвращается в каждом HTTP-ответе и используется для трассировки операций.
