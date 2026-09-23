# Security / Безопасность — Remnawave VPN Shop 3.1.6

## Аудит 3.1.6 / 3.1.6 audit

- Админка, Mini App и кабинет остаются с `read_only: true`. nginx пишет только в tmpfs `/tmp/nginx`. Конфиг смонтирован только для чтения. Caddy не публикует домен, пока `GET /` панели не ответил.
- The admin UI, Mini App, and cabinet stay `read_only: true`. nginx writes only on the `/tmp/nginx` tmpfs. The config is mounted read-only. Caddy does not publish the domain until the panel's `GET /` has answered.

## Аудит 3.1.5 / 3.1.5 audit

- Админка, Mini App и кабинет остаются с `read_only: true`. Запись nginx идёт только в tmpfs `/tmp`, `/var/cache/nginx` и `/run`. В **3.1.4** отсутствие этих каталогов роняло процесс, и Caddy отвечал 502, пока контейнер перезапускался.
- The admin UI, Mini App, and cabinet stay `read_only: true`. nginx writes only on the tmpfs mounts `/tmp`, `/var/cache/nginx`, and `/run`. In **3.1.4** the missing directories crashed the process, and Caddy answered 502 while the container restarted.

## Аудит 3.1.4 / 3.1.4 audit

- Два процесса больше не создают `alembic_version` одновременно. Проигравший в **3.1.3** завершал контейнер API до `/health`, и `docker compose up` сообщал `container vpn-shop-backend-1 is unhealthy`.
- Ответы установщика обрезаются по краям. Имя `Moscow` заменяется на `Europe/Moscow`, потому что PostgreSQL не принимает `TimeZone=Moscow`.
- Two processes no longer create `alembic_version` at the same time. In **3.1.3** the loser exited the API container before `/health`, and `docker compose up` reported `container vpn-shop-backend-1 is unhealthy`.
- Installer answers are trimmed. The name `Moscow` is replaced with `Europe/Moscow`, because PostgreSQL rejects `TimeZone=Moscow`.

## Аудит 3.1.3 / 3.1.3 audit

- `curl | bash` больше не читает ответы оператора из исчерпанного stdin. Вопросы идут с `/dev/tty`. Секретные поля по-прежнему скрыты `read -s`. Без терминала установщик останавливается и просит `INSTALL_NONINTERACTIVE=1`, а не обрывается на пустом `read`.
- `curl | bash` no longer reads operator answers from an exhausted stdin. Questions come from `/dev/tty`. Secret fields stay hidden with `read -s`. Without a terminal the installer stops and asks for `INSTALL_NONINTERACTIVE=1` instead of failing on an empty `read`.

## Аудит 3.1.2 / 3.1.2 audit

- `GET /api/admin/remnawave/users/{id}/subscription` и `GET /api/admin/remnawave/users/{id}/keys` требуют `users.keys`. Роль `viewer` это право не имеет. Списки, поток и карточка проходят `redact_remote` и не содержат ссылку подписки, `shortUuid` и пароли протоколов. Обзор отдаёт только `response.total`.
- Диагностика, задания, копии, провайдеры, выплаты, мониторы, операции восстановления и проверка копии отдают `error` и `last_error` как `unavailable`. stderr `psql` и `alembic` в HTTP-ответ восстановления не попадает.
- `GET /api/admin/audit` заменяет в JSON ключи `error`, `token`, `secret`, `password` и `authorization` на `unavailable`. Причина возврата обрезается перед хвостом с текстом исключения. Оповещение Telegram о сбое копии и планировщика возвратов текст исключения не содержит.
- Установка узла по SSH отвечает `Remote install failed` и не возвращает вывод `docker compose`.

- `GET /api/admin/remnawave/users/{id}/subscription` and `GET /api/admin/remnawave/users/{id}/keys` require `users.keys`. Role `viewer` does not have that permission. Lists, the stream, and the user card pass through `redact_remote` and omit the subscription URL, `shortUuid`, and protocol passwords. Overview returns only `response.total`.
- Diagnostics, jobs, backups, providers, payouts, monitors, recovery operations, and backup verification return `error` and `last_error` as `unavailable`. `psql` and `alembic` stderr do not enter the restore HTTP response.
- `GET /api/admin/audit` replaces JSON keys `error`, `token`, `secret`, `password`, and `authorization` with `unavailable`. A refund reason is cut before the tail that carried exception text. The Telegram alert for a backup failure and for the refund scheduler does not include the exception text.
- SSH node install answers `Remote install failed` and does not return `docker compose` output.

## Аудит 3.1.1 / 3.1.1 audit

- Повторное сохранение staging-конфигурации подставляет прежний секрет, Shop ID или Merchant ID, если новое поле пустое. Сравнение с production-ключами идёт по уже объединённым значениям, поэтому пустая форма не прячет боевой ключ, оставшийся в базе.
- Журнал раннера проходит `_redact_staging_output`. Токен Remnawave, bearer пользователя, runner token и секреты касс длиной от 8 символов заменяются на `[скрыто]` и в stdout, и в тексте исключения. Shop ID и Merchant ID остаются, потому что они могут быть частью https-адреса `[CHECKOUT]`.
- Production gate по-прежнему требует статус `passed`, `full_e2e` и строку `FULL_E2E_PASS` не старше 24 часов. Статус `awaiting_checkout` gate не включает. Сохранение конфигурации и кнопка **Заблокировать** ставят gate в `0`.
- Образ backend ставит `curl`, иначе `/app/staging-e2e.sh` завершается до проверки `/health`.

- A later staging-config save keeps the previous secret, Shop ID, or Merchant ID when the new field is blank. The production-credential comparison uses the merged values, so a blank form cannot hide a live key that is already stored.
- The runner log passes through `_redact_staging_output`. The Remnawave token, the user bearer, the runner token, and cashier secrets of 8 characters or more become `[скрыто]` in stdout and in the exception text. Shop ID and Merchant ID stay, because they can be part of the `[CHECKOUT]` https URL.
- The production gate still requires status `passed`, `full_e2e`, and the line `FULL_E2E_PASS` younger than 24 hours. Status `awaiting_checkout` does not enable the gate. A config save and **Заблокировать** (Block) set the gate to `0`.
- The backend image installs `curl`. Without it, `/app/staging-e2e.sh` exits before the `/health` check.

## Аудит 3.1.0 / 3.1.0 audit

- `GET /api/plans` не включает `remnawave_profile_id`. Внутренний идентификатор профиля Remnawave остаётся у администратора и в снимке платежа.
- `GET /api/me/auto-renew` не возвращает `method.last_error`. Покупатель видит фиксированную фразу «Автопродление не выполнено».
- SHA-256 пакета считается по байтам файла и проходит `safe_sha256`: 64 шестнадцатеричных символа. Имя файла на диске в JSON не попадает.
- `GET /api/me/subscription-file` требует сессию покупателя, отвечает `Cache-Control: private, no-store` и отбрасывает ссылку с переводом строки.
- `GET /api/public/apps/install` отдаёт публичные карточки и уже опубликованные ссылки GitHub. Карточки администратора магазина в `shop_apps` не входят.

- `GET /api/plans` does not include `remnawave_profile_id`. The Remnawave profile id stays with the administrator and on the payment snapshot.
- `GET /api/me/auto-renew` does not return `method.last_error`. The buyer sees the fixed sentence «Автопродление не выполнено».
- The package SHA-256 is computed from the file bytes and passes `safe_sha256`: 64 hexadecimal characters. The stored file name is not returned in JSON.
- `GET /api/me/subscription-file` requires a buyer session, answers `Cache-Control: private, no-store` and drops a URL that contains a newline.
- `GET /api/public/apps/install` returns the public cards and the GitHub links that are already published. Shop administrator cards are not included in `shop_apps`.

## Аудит 3.0.1 / 3.0.1 audit

- Автопродление YooKassa и проверка шифрованной резервной копии вызывают `decrypt_secret` из пакета приложения. Импорт `backend.app.security` в контейнере `uvicorn app.main:app` не существует и больше не используется.
- `POST /api/me/wallet/spend` без заголовка `Idempotency-Key` отвечает 400. Сервер не подставляет случайный ключ. Повтор с тем же ключом, в том числе пока первая операция ещё держит блокировку пользователя, возвращает уже созданный платёж и не списывает баланс второй раз.
- Другой ключ на тот же тариф, ту же цену и тот же промокод в течение 30 секунд отвечает 409 «Повторное списание с баланса заблокировано. Подождите полминуты и повторите покупку.»
- `POST /api/me/gifts/purchase` повторно ищет подарок по ключу идемпотентности уже под блокировкой пользователя, поэтому параллельный повтор не создаёт второй код и не отвечает 500.
- `POST /api/payments/create` с новым ключом не открывает второй сеанс провайдера, пока в последние 30 секунд у того же снимка тарифа есть счёт в состоянии `creating`, `pending` или `creation_unknown`. Готовый счёт `pending` возвращается снова.

- Auto-renew and encrypted backup validation call `decrypt_secret` from the application package. The import `backend.app.security` does not exist in the `uvicorn app.main:app` container and is no longer used.
- `POST /api/me/wallet/spend` without an `Idempotency-Key` header answers 400. The server does not invent a random key. A retry with the same key, including while the first operation still holds the user lock, returns the payment already created and does not debit the balance again.
- A different key for the same plan, price and promo code within 30 seconds answers 409 «Повторное списание с баланса заблокировано. Подождите полминуты и повторите покупку.»
- `POST /api/me/gifts/purchase` looks up the gift by idempotency key again while the user row is locked, so a parallel retry does not create a second code and does not answer 500.
- `POST /api/payments/create` with a new key does not open a second provider session while the same plan snapshot has an invoice in `creating`, `pending` or `creation_unknown` from the last 30 seconds. An existing `pending` invoice is returned again.

## Аудит 3.0.0-realise / 3.0.0-realise audit

- Общий потолок тела запроса остаётся 12 МБ. Для `POST /api/admin/apps/{id}/file` при наличии `Content-Length` потолок равен 80 МБ, как у `MAX_PACKAGE_BYTES`. Запрос без длины по-прежнему обрезается на 12 МБ, чтобы не буферизовать 80 МБ до авторизации.
- Зависимость `manage_content` стоит раньше `UploadFile`, поэтому отказ в праве происходит до чтения пакета.
- Клиенты с токеном бота, секретом Яндекса и токеном Remnawave создаются с `trust_env=False`. Переменные `HTTP_PROXY` и `HTTPS_PROXY` не получают URL с секретом.
- `_client_ip` читает `X-Forwarded-For` только от loopback, частного или link-local соседа. Публичный прямой клиент не подменяет IP вебхука.
- `POST /api/admin/payments/{id}/retry`, повтор операции выдачи и `GET /api/admin/health/summary` не кладут `str(exception)` в JSON. Текст исключения пишется в журнал.
- Пароль считается scrypt с тем же коэффициентом и `maxmem` 64 МиБ.
- `audit_logs.request_id` есть в модели. Суммы Decimal и даты в журнале сериализуются, а не роняют запрос.
- Флаг функции выбирается по `FeatureFlag.key`. Пустая таблица не даёт 500 на создании платежа.
- Vite в панелях `admin`, `miniapp` и `cabinet` — `7.3.6`. Предыдущий pin `7.1.5` попадал в предупреждения `npm audit` для dev-сервера.

- The global request body ceiling stays 12 MB. `POST /api/admin/apps/{id}/file` with `Content-Length` uses the 80 MB `MAX_PACKAGE_BYTES` ceiling. A request without a length is still cut at 12 MB so an 80 MB body is not buffered before authorization.
- The `manage_content` dependency is declared before `UploadFile`, so a missing permission fails before the package is read.
- Clients that carry the bot token, the Yandex secret or the Remnawave token are created with `trust_env=False`. `HTTP_PROXY` and `HTTPS_PROXY` do not receive a URL that contains a secret.
- `_client_ip` reads `X-Forwarded-For` only from a loopback, private or link-local peer. A public direct client cannot spoof a webhook IP.
- `POST /api/admin/payments/{id}/retry`, the provisioning retry and `GET /api/admin/health/summary` do not put `str(exception)` in JSON. The exception text is written to the log.
- Passwords use the same scrypt work factor with `maxmem` of 64 MiB.
- `audit_logs.request_id` is mapped on the model. Decimal amounts and datetimes in the audit log are serialized and do not fail the request.
- A feature flag is selected by `FeatureFlag.key`. An empty table does not make payment creation answer 500.
- Vite in the `admin`, `miniapp` and `cabinet` panels is `7.3.6`. The previous pin `7.1.5` matched high `npm audit` findings for the dev server.

## Файлы приложений / App packages (2.13.0)

- Загрузка APK и IPA требует `manage_content`. Скачивание в панели требует `read`. Публичная ссылка есть только у включённой карточки покупателя.
- Пакет проверяется по расширению и подписи ZIP `PK`. Размер не больше 80 МБ. Имя на диске — 32 шестнадцатеричных символа, его нет в JSON.
- Каталог `app-packages` не смонтирован как `/media`. Подмена пути `..` отклоняется и при чтении, и при восстановлении из копии.
- Сохранение текстов карточки не принимает имя файла от браузера и не затирает уже загруженный пакет.

- Uploading an APK or IPA requires `manage_content`. A panel download requires `read`. A public link exists only for an enabled buyer card.
- The package is checked by extension and the ZIP `PK` signature. The size limit is 80 MB. The on-disk name is 32 hexadecimal characters and is absent from JSON.
- The `app-packages` directory is not mounted as `/media`. A `..` path is rejected when reading and when restoring a backup.
- Saving card text does not accept a file name from the browser and does not erase an uploaded package.

## Рассылка / Broadcast (2.12.0)

- Поставить или повторить рассылку может только роль с `manage_broadcasts` (`operator`, `admin`).
- Текст уходит в Telegram как HTML, который ввёл оператор. Это ожидаемый режим панели, не фильтр для покупателя.
- `button_url` и `image_url` проходят `validate_public_url`: только абсолютный HTTPS, без логина и пароля, без частного адреса. Пустое значение допускается.
- Кнопка принимается только парой «текст + URL». Подпись к картинке не длиннее 1024 символов.
- Воркер ходит в `api.telegram.org` с `trust_env=False` и не подставляет прокси из окружения процесса.
- Повтор не обнуляет счётчики. Уже учтённые получатели пропускаются. Завершённая рассылка повторно не стартует.

- Only a role with `manage_broadcasts` (`operator`, `admin`) can queue or retry a broadcast.
- The text is sent to Telegram as the HTML the operator typed. That is the panel mode.
- `button_url` and `image_url` go through `validate_public_url`: absolute HTTPS, no username or password, no private address. An empty value is allowed.
- A button is accepted only as a text and URL pair. An image caption is at most 1024 characters.
- The worker calls `api.telegram.org` with `trust_env=False` and does not apply process proxy variables.
- Retry does not reset the counters. Recipients already counted are skipped. A completed broadcast does not start again.

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
