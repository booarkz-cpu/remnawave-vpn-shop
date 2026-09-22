# Security / Безопасность — Remnawave VPN Shop 2.5.0

Граница доверия: браузер или Telegram → Caddy → API → PostgreSQL, Redis, Remnawave и платёжные провайдеры. PostgreSQL и Redis наружу не публикуются.

Trust boundary: browser or Telegram → Caddy → API → PostgreSQL, Redis, Remnawave and the payment providers. PostgreSQL and Redis are not published to the host network.

Предыдущая версия документа описывала 2.4.0. Ниже — актуальная модель 2.5.0 на двух языках.

## Аутентификация

- Администратор: пароль scrypt, необязательный TOTP, коды восстановления, JWT только вместе с записью `AdminSession`.
- Сессия администратора живёт в HttpOnly cookie `rw_admin`, привязана к User-Agent, гаснет через 15 минут простоя и не дольше абсолютного срока токена.
- Покупатель: Telegram initData (HMAC), email+пароль (scrypt), опциональные VK ID и Yandex ID. Cookie `rw_user` — HttpOnly.
- Мутации с cookie требуют заголовок `X-CSRF-Token`, равный cookie `rw_csrf`. Вебхуки и первичный вход (`/api/auth/login`, `/api/auth/register`, Telegram, VK, Яндекс, exchange, вход администратора) из этого правила исключены.
- Rate limit на вход, регистрацию, OAuth, создание платежа, sandbox complete, публичный статус серверов и список конструкторов.
- RBAC: `viewer`, `operator`, `admin`. Конструктор тарифов требует `manage_plans`. Мониторинг узлов требует `read`. Недостаточное право отвечает 403.

## Платежи

- Намерение платежа записывается до вызова провайдера. Повтор с тем же `Idempotency-Key` не создаёт второе списание.
- Ключ, уже использованный для другого `plan_id` или другой конфигурации конструктора (другие дни, трафик или устройства), отвечает 409.
- Снимок `duration_days_snapshot`, `traffic_limit_gb_snapshot`, `device_limit_snapshot` и профиля фиксируется в момент оплаты. Позднее изменение конструктора не переписывает уже купленное право.
- Якорный тариф конструктора скрыт из `GET /api/plans`. Прямая покупка, пробный период и подарок по его `plan_id` без выбранных пунктов конструктора отклоняются: иначе можно было бы заплатить только базовую цену.
- YooKassa: вебхук отклоняется, если `YOOKASSA_WEBHOOK_IP_ALLOWLIST` пуст или IP отправителя не входит в список. Пустой список не означает «принять всех».
- После вебхука API сам читает платёж у провайдера и сверяет статус, сумму, валюту и `order_id`. Текст вебхука не является доказательством оплаты.
- Platega: заголовки магазина. RollyPay: HMAC и окно timestamp 5 минут.
- `SandboxProvider` активен только при `PAYMENTS_SANDBOX=true` и не принимает чужие payment id вне префикса `sandbox-`. Боевой production gate для провайдера `sandbox` обходится только в этом режиме.
- Возврат идемпотентен по ключу `refund-{payment_id}`. Отзыв VPN не выполняется, если есть более новая успешно выданная оплата.
- Боевые платежи выключены, пока администратор не включит production gate после staging E2E. Staging не читает production-секреты провайдеров.

## Статус серверов Remnawave

- `GET /api/public/servers`, `GET /api/me/servers` и `GET /api/admin/remnawave/monitoring` отдают только имя, код страны, статус (`online`, `offline`, `disabled`, `unknown`) и число пользователей онлайн.
- Публичный ответ не отдаёт адреса, порты, токены, пароли и сырой JSON панели. Имя узла, похожее на URL или IP, заменяется на `node`.
- Ошибка панели для клиента — текст «Remnawave недоступен», без текста исключения и без внутреннего URL.
- `GET /api/admin/remnawave/nodes` и `GET /api/admin/remnawave/health` используют тот же очищенный формат. Обзор админки больше не кладёт сырой список узлов и `str(exception)` в JSON.
- Пользовательский ответ добавляет только флаг `subscription_active`. Он не добавляет ключи подключения.

## Сеть и файлы

- Исходящие запросы к платёжным API идут через DNS-pinned клиент: адрес проверяется на публичность, соединение открывается на проверенный IP, TLS сохраняет исходное имя. Редиректы выключены, `trust_env=False`.
- Загрузка изображений ограничена типом, сигнатурой и размером. Файл перекодируется. Удаление старого файла берёт только basename внутри `MEDIA_DIR`.
- Тело запроса без `Content-Length` читается потоково и обрывается после 12 МиБ. Некорректный `Content-Length` отвечает 400.
- Каталоги `MEDIA_DIR` (`/data/media`), `BACKUPS_DIR` (`/data/backups`) и `PROJECT_DIR` (`/project`) заданы в конфигурации и совпадают с томами Docker Compose.
- Архив бэкапа открывается только внутри своего каталога. Восстановление требует явного подтверждения.
- SSH-провижининг узла требует отпечаток host key. Секреты SSH не пишутся в постоянное хранилище приложения как учётные данные панели.

## Секреты

- `APP_SECRET` не короче 32 символов. Им подписываются JWT и шифруются TOTP, коды восстановления и staging-конфиг.
- `APP_SECRET_PREVIOUS` нужен только на время ротации.
- Метрики закрыты `METRICS_TOKEN`. Публичный OpenAPI выключен.
- В git не храните `.env` и живые ключи. Пример — `.env.example`.

## Кошелёк, подарки и канал

- Пополнение кошелька — обычный платёж с `purpose=topup`. Зачисление происходит только после сверки оплаты и под блокировкой платежа, один раз.
- Оплата тарифа и покупка подарка списывают `wallet_balance` под блокировкой пользователя. Повтор с тем же `Idempotency-Key` не списывает сумму второй раз.
- Покупатель подарка не может активировать собственный код. Повторная активация тем же получателем не продлевает подписку второй раз.
- Если задан `REQUIRED_TELEGRAM_CHANNEL`, оплата и списание кошелька требуют членства в канале. Ошибка Telegram API отвечает 503 и не создаёт списание.

## Что это не гарантирует

Gate production не заменяет внешнюю проверку провайдера. Панель не включает WebAuthn автоматически: хранилище ключей есть, криптографическая проверка assertion не притворяется включённой 2FA. Живые кассы YooKassa, Platega, RollyPay и боевой Remnawave в этом репозитории не прогоняются. Sandbox подтверждает только локальный контур оплаты.

---

# Security (English)

## Authentication

Admin passwords use scrypt. Optional TOTP and recovery codes are encrypted. The admin JWT is accepted only together with an `AdminSession`. The session cookie is HttpOnly, bound to the user agent, and expires after 15 minutes of idle time and at the token's absolute expiry.

Buyers sign in with verified Telegram initData, email and a scrypt password, and optional VK ID or Yandex ID. The buyer cookie `rw_user` is HttpOnly. Cookie mutations require `X-CSRF-Token` equal to `rw_csrf`. Webhooks and the first-login routes are exempt. Login, registration, OAuth, payment creation, sandbox completion, the public server list and the constructor list are rate limited.

RBAC roles are `viewer`, `operator` and `admin`. Creating a tariff constructor requires `manage_plans`. Node monitoring requires `read`. A missing permission returns 403.

## Payments

A payment intent is stored before the provider call. Reusing an `Idempotency-Key` does not create a second charge. Reusing it for another plan or another constructor selection (different days, traffic or devices) returns 409.

Duration, traffic, device limit and Remnawave profile are snapshotted on the payment. Later edits of the constructor do not change an already purchased entitlement.

The constructor's anchor plan is hidden from `GET /api/plans`. Buying, trialing or gifting that plan id without constructor options is rejected, so a client cannot pay only the base price and skip option prices.

YooKassa webhooks fail closed when `YOOKASSA_WEBHOOK_IP_ALLOWLIST` is empty or does not match the sender. Fulfillment still re-reads the provider payment and checks status, amount, currency and order id. Platega uses shop headers. RollyPay uses HMAC and a five-minute timestamp window.

`SandboxProvider` runs only when `PAYMENTS_SANDBOX=true` and only accepts ids with the `sandbox-` prefix. The production payment gate is bypassed for that provider only in sandbox mode. Refunds are idempotent on `refund-{payment_id}`. Live payments stay disabled until an administrator opens the production gate after staging E2E.

## Remnawave server status

`GET /api/public/servers`, `GET /api/me/servers` and `GET /api/admin/remnawave/monitoring` return a name, a country code, a status (`online`, `offline`, `disabled`, `unknown`) and an online-user count.

The public payload does not return addresses, ports, tokens, passwords or the raw panel JSON. A node name that looks like a URL or an IP address is replaced with `node`. A panel failure is reported as “Remnawave недоступен” without the exception text or the internal URL.

`GET /api/admin/remnawave/nodes`, `GET /api/admin/remnawave/health` and the admin overview use the same sanitized node shape. The user payload adds only `subscription_active`. It does not add connection keys.

## Network, files and secrets

Outbound payment HTTP uses a DNS-pinned client: the address must be public, the socket connects to that IP, TLS keeps the original name, redirects are disabled and `trust_env` is false. Uploaded media is type-checked, re-encoded, and deleted by basename inside `MEDIA_DIR`. Chunked bodies stop after 12 MiB. An invalid `Content-Length` returns 400.

`APP_SECRET` must be at least 32 characters. It signs JWTs and encrypts TOTP, recovery codes and the staging config. Metrics require `METRICS_TOKEN`. Public OpenAPI is disabled. Do not commit `.env`.

Wallet top-ups credit `wallet_balance` once, after provider confirmation, under the payment lock. Wallet spend and gift purchase debit the balance under the user lock. A gift buyer cannot redeem their own code. A required Telegram channel check returns 503 on a Telegram API failure and does not create a charge.

## Limits

The production gate does not replace a provider's own verification. Passkeys are stored but are not presented as active MFA. Live YooKassa, Platega, RollyPay and a production Remnawave panel are not exercised by this repository. The sandbox script proves the local checkout path only.
