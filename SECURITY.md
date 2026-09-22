# Security / Безопасность — Remnawave VPN Shop 2.11.0

Граница доверия: браузер или Telegram → Caddy → API → PostgreSQL, Redis, Remnawave и платёжные провайдеры. PostgreSQL и Redis наружу не публикуются.

Trust boundary: browser or Telegram → Caddy → API → PostgreSQL, Redis, Remnawave and the payment providers. PostgreSQL and Redis are not published to the host network.

Предыдущая версия документа описывала 2.9.0, 2.6.0, 2.5.0 и 2.4.0. Ниже — актуальная модель 2.10.0 на двух языках. Платформа 2.6.0 сохранена.

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

## Платформа 2.6.0

- Токен агента, ключ API и секрет webhook возвращаются только в ответе на создание. `GET /api/admin/platform/summary` отдаёт имя агента, префикс ключа и URL webhook и не отдаёт `token_hash`, `secret_hash` и расшифрованный секрет.
- Агент авторизуется заголовком `X-Agent-Token`. Сервер хранит SHA-256 токена. Heartbeat помечает доставленными только действия `throttle` и `clear`. Остальные виды в очереди получают статус `rejected` и на узел не уходят.
- Наблюдения с некорректным IP не сохраняются. Сырые адреса остаются в таблице наблюдений и видны администратору с правом `read`. Публичные маршруты серверов по-прежнему не отдают адреса.
- Пользователь с `restricted_at` получает 403 «Доступ ограничен» на пробный период, создание платежа и списание кошелька.
- HWID со действием `block` получает 403 «Устройство в чёрном списке». Действие `alert` регистрацию не останавливает.
- `auto_hard_block` по умолчанию выключен.
- Ключ API имеет вид `rw_` и проверяется по хешу и scope. `GET /api/v3/status` требует scope `read`.
- Webhook создаётся только для URL, который проходит `validate_public_url`. Подпись — HMAC-SHA256 тела в `X-Shop-Signature`. Ошибка доставки записывается как «delivery failed» без текста исключения.
- Тест SMTP отправляет письмо только на `admin.email` текущего администратора. Пароль SMTP и закрытый ключ DKIM лежат в `AppSetting` в виде `encrypt_secret`.
- Дополнительные строки Prometheus появляются, когда модуль `metrics` включён. Сам `/metrics` по-прежнему закрыт `METRICS_TOKEN`.

## Мобильные приложения 2.7.0

- Веб-вход администратора и покупателя по-прежнему кладёт JWT только в HttpOnly cookie и не возвращает `access_token` в JSON.
- Нативный клиент получает `access_token`, только если заголовок `X-Shop-Client` равен `android-user`, `android-admin`, `ios-user` или `ios-admin`. Другое значение оставляет веб-путь с cookie.
- Приложение хранит токен локально и шлёт `Authorization: Bearer`. Cookie оно не сохраняет, поэтому заголовок `X-CSRF-Token` для этих вызовов не требуется.
- Сессия привязана к User-Agent. Строки приложений фиксированы: `RemnawaveShop-Android-User/2.9.0`, `RemnawaveShop-Android-Admin/2.9.0`, `RemnawaveShop-iOS-User/2.9.0`, `RemnawaveShop-iOS-Admin/2.9.0`. Смена строки отзывает сессию. Строки **2.8.0** остаются в истории релизов и для новой сессии не подходят.
- Клиенты не следуют HTTP-редиректам и не пишут токен в журнал. Платёжный URL открывается только для https или для `localhost`, `127.0.0.1` и `10.0.2.2`.
- Экран узлов повторно оставляет поля `name`, `country`, `status`, `users_online`. Имя с признаками хоста заменяется на `node`.

## Приложения 2.10.0

- Запрос с известным `X-Shop-Client` при `MOBILE_REQUIRE_PROOF=true` должен содержать `X-Shop-Time` и `X-Shop-Proof`. Сообщение: `{client}\n{unix}\n{METHOD}\n{path}` без query. HMAC-SHA256, окно 300 секунд, сравнение через `hmac.compare_digest`. Ошибка — 401 «Подпись клиента не принята».
- Без заголовка клиента веб-вход на cookie не меняется.
- Ключ по умолчанию записан в исходниках и в APK. Это останавливает случайную подделку заголовка. Извлечённый ключ оператор меняет через `MOBILE_CLIENT_KEY` и пересборку приложений. `MOBILE_REQUIRE_PROOF=false` принимает приложения 2.9.0.
- User-Agent 2.10.0: `RemnawaveShop-Android-User/2.10.0`, `RemnawaveShop-Android-Admin/2.10.0`, `RemnawaveShop-iOS-User/2.10.0`, `RemnawaveShop-iOS-Admin/2.10.0`. Смена строки начинает новую сессию. Строки 2.9.0 остаются в истории.
- `GET /api/me/devices` не возвращает `device_key` и `last_ip`. Карточка платежа администратора не возвращает `fulfillment_error`, `checkout_url` и `provider_payment_id`.
- Сохранённый токен в приложении закрыт биометрией или PIN. Устройство без этого способа открывается сразу, чтобы телефон не остался заблокированным.
- `GET /api/admin/github-update` только читает метаданные релиза. API не скачивает и не распаковывает архив. Скрипт на хосте сверяет SHA-256, отклоняет symlink и путь с `..`, не затирает `.env` и вызывает `scripts/update.sh`. С версии 2.11.0 снимок и `pg_dump` делаются до копирования новых файлов.

## Пакеты Android 2.9.0

- Релиз публикует два APK, подписанных отладочным ключом сборки. Это пакеты для ручной установки. Для Google Play нужна отдельная подпись владельца.
- Платёжный URL разбирается как адрес. Схема `https` принимается. Схема `http` принимается только если хост равен `localhost`, `127.0.0.1` или `10.0.2.2`. Логин в адресе и пробелы отклоняются.
- APK не коммитятся в git. Архив исходников их тоже не содержит. Проверка файла — по `.sha256` рядом с релизом.

## Каталог приложений 2.8.0

- `GET /api/public/apps` возвращает `logo_url` и включённые карточки с `audience=user`. Карточки администратора и выключенные карточки в ответ не входят.
- Ссылка карточки сохраняется только как абсолютный `https` без логина, пароля и локального адреса. Пустая ссылка допустима.
- `logo_url` — только путь `/media/<имя файла>`. `..`, схема и дополнительные сегменты отбрасываются.
- Загрузка логотипа требует `manage_content`, перекодирует изображение в PNG и удаляет предыдущий файл по имени внутри `MEDIA_DIR`.

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

## Platform 2.6.0

The agent token, API key and webhook secret are returned only from the create response. The platform summary returns the agent name, the key prefix and the webhook URL. It does not return `token_hash`, `secret_hash` or a decrypted secret.

The agent authenticates with `X-Agent-Token`. The server stores the SHA-256 of the token. Heartbeat marks only `throttle` and `clear` as delivered. Any other queued kind is marked `rejected` and is not sent to the node.

Observations with an invalid IP are dropped. Raw addresses stay in the observation table for an administrator with `read`. Public server routes still omit addresses.

A user with `restricted_at` receives 403 on trial, payment creation and wallet spend. An HWID blacklist action `block` returns 403 on device registration. An action `alert` does not stop registration. `auto_hard_block` is off by default.

An API key starts with `rw_` and is checked by hash and scope. `GET /api/v3/status` requires the `read` scope. A webhook URL must pass `validate_public_url`. The body is signed with HMAC-SHA256 in `X-Shop-Signature`. A delivery failure is stored as “delivery failed” without the exception text.

The SMTP test sends only to the current administrator's `admin.email`. The SMTP password and the DKIM private key are stored with `encrypt_secret`. Extra Prometheus lines are emitted when the `metrics` module is enabled. `/metrics` itself still requires `METRICS_TOKEN`.

## Mobile apps 2.7.0

Web admin and buyer login still store the JWT only in an HttpOnly cookie and do not return `access_token` in JSON. A native client receives `access_token` only when `X-Shop-Client` is `android-user`, `android-admin`, `ios-user` or `ios-admin`. Any other value keeps the cookie path.

The app stores the token locally and sends `Authorization: Bearer`. It does not persist cookies, so `X-CSRF-Token` is not required for those calls. The session stays bound to the User-Agent. The app strings are fixed: `RemnawaveShop-Android-User/2.9.0`, `RemnawaveShop-Android-Admin/2.9.0`, `RemnawaveShop-iOS-User/2.9.0` and `RemnawaveShop-iOS-Admin/2.9.0`. Changing the string revokes the session. The **2.8.0** strings belong to the previous release.

Clients do not follow HTTP redirects and do not log the token. A payment URL opens only for https or for `localhost`, `127.0.0.1` and `10.0.2.2`. The node screen keeps `name`, `country`, `status` and `users_online`, and replaces a host-like name with `node`.

## Apps 2.10.0

A request that names a known `X-Shop-Client` while `MOBILE_REQUIRE_PROOF=true` must send `X-Shop-Time` and `X-Shop-Proof`. The HMAC-SHA256 message is `{client}\n{unix}\n{METHOD}\n{path}` with no query. The window is 300 seconds and the compare uses `hmac.compare_digest`. Failure is HTTP 401. A browser request without the client header keeps the cookie session.

The default key is in the source and in the APK. It stops a casual header spoof. An operator who sets `MOBILE_CLIENT_KEY` rebuilds the apps. `MOBILE_REQUIRE_PROOF=false` keeps the 2.9.0 apps working.

The 2.10.0 User-Agent strings are `RemnawaveShop-Android-User/2.10.0`, `RemnawaveShop-Android-Admin/2.10.0`, `RemnawaveShop-iOS-User/2.10.0` and `RemnawaveShop-iOS-Admin/2.10.0`. A changed string starts a new session. The 2.9.0 strings stay in the history.

`GET /api/me/devices` omits `device_key` and `last_ip`. The admin payment card omits `fulfillment_error`, `checkout_url` and `provider_payment_id`. A saved token is locked with biometrics or the device PIN. A device that cannot authenticate opens immediately.

`GET /api/admin/github-update` reads release metadata only. The API does not download or extract the archive. The host script checks SHA-256, rejects a symlink and a `..` path, keeps `.env` and runs `scripts/update.sh`. From 2.11.0 the snapshot and `pg_dump` happen before the new files are copied.

## Android packages 2.9.0

The release publishes two APKs signed with the build machine's debug key. They are sideload packages. A Play Store upload needs the owner's own signing key. A payment URL is parsed before it opens: `https` is accepted, and `http` is accepted only for the hosts `localhost`, `127.0.0.1` and `10.0.2.2`. User info and whitespace are rejected. The APK files stay out of git and out of the source archive. Check each file with the `.sha256` published next to the release.

## App catalog 2.8.0

`GET /api/public/apps` returns `logo_url` and enabled cards whose audience is `user`. Administrator cards and disabled cards are omitted. A card link is stored only as an absolute `https` URL without user info or a local host. An empty link is allowed.

`logo_url` is only a `/media/<filename>` path. `..`, a scheme and extra path segments are dropped. Logo upload requires `manage_content`, re-encodes the image to PNG and deletes the previous file by basename inside `MEDIA_DIR`.

## Limits

The production gate does not replace a provider's own verification. Passkeys are stored but are not presented as active MFA. Live YooKassa, Platega, RollyPay and a production Remnawave panel are not exercised by this repository. The sandbox script proves the local checkout path only.
