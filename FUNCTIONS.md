# Разбор функций / Function reference

Версия приложения: **3.1.6**. Панели nginx — раздел 9.20 `INSTRUCTION.md` и `RELEASE_NOTES_V3_1_6.md`. Версия приложения предыдущего релиза: **3.1.5**. Полное описание модулей и их назначения — в `MODULES.md` (русский и английский). Функции четырёх приложений и установка APK — в `MOBILE.md`. Пошаговая установка — `INSTALL_STEPS.md`. Панели nginx — раздел 9.19 `INSTRUCTION.md` и `RELEASE_NOTES_V3_1_5.md`. Первый запуск API — раздел 9.18 `INSTRUCTION.md` и `RELEASE_NOTES_V3_1_4.md`. Установка через канал — раздел 9.17 `INSTRUCTION.md` и `RELEASE_NOTES_V3_1_3.md`. Аудит ответов панели — раздел 9.16 `INSTRUCTION.md` и `RELEASE_NOTES_V3_1_2.md`. Staging E2E и production gate — раздел 9.15 `INSTRUCTION.md` и `RELEASE_NOTES_V3_1_1.md`. Состав 3.1.0 — раздел 9.14 и `RELEASE_NOTES_V3_1_0.md`. Исправления 3.0.1 — раздел 9.13 и `RELEASE_NOTES_V3_0_1.md`. Исправления 3.0.0-realise — раздел 9.12 и `RELEASE_NOTES_V3_0_0.md`.

Application version: **3.1.6**. The nginx panels are section 9.20 of `INSTRUCTION.md` and `RELEASE_NOTES_V3_1_6.md`. The previous application version was **3.1.5**. Module purposes are in `MODULES.md`. The four apps and the APK install are in `MOBILE.md`. The step-by-step install is `INSTALL_STEPS.md`. The nginx panels are section 9.19 of `INSTRUCTION.md` and `RELEASE_NOTES_V3_1_5.md`. The API first boot is section 9.18 of `INSTRUCTION.md` and `RELEASE_NOTES_V3_1_4.md`. The piped install is section 9.17 of `INSTRUCTION.md` and `RELEASE_NOTES_V3_1_3.md`. The panel-response audit is section 9.16 of `INSTRUCTION.md` and `RELEASE_NOTES_V3_1_2.md`. Staging E2E and the production gate are section 9.15 of `INSTRUCTION.md` and `RELEASE_NOTES_V3_1_1.md`. The 3.1.0 changes are section 9.14 and `RELEASE_NOTES_V3_1_0.md`. The 3.0.1 fixes are section 9.13 and `RELEASE_NOTES_V3_0_1.md`. The 3.0.0-realise fixes are section 9.12 and `RELEASE_NOTES_V3_0_0.md`.

## Аудит 3.1.6 / 3.1.6 audit

`deploy/nginx/nginx.conf` задаёт `pid` и `client_body_temp_path` внутри `/tmp/nginx`. Compose монтирует этот файл в `admin`, `miniapp` и `cabinet` и проверяет `GET /` до старта Caddy.

`deploy/nginx/nginx.conf` sets `pid` and `client_body_temp_path` under `/tmp/nginx`. Compose mounts that file into `admin`, `miniapp`, and `cabinet` and checks `GET /` before Caddy starts.

## Аудит 3.1.5 / 3.1.5 audit

`docker-compose.yml` даёт сервисам `admin`, `miniapp` и `cabinet` tmpfs `/var/cache/nginx` и `/run` при `read_only: true`. Установщик после `docker compose up` проверяет, что эти сервисы не в `restarting`.

`docker-compose.yml` gives `admin`, `miniapp`, and `cabinet` tmpfs mounts for `/var/cache/nginx` and `/run` while `read_only: true`. After `docker compose up` the installer checks that those services are not `restarting`.

## Аудит 3.1.4 / 3.1.4 audit

`alembic/env.py` берёт `pg_advisory_xact_lock` до `CREATE TABLE alembic_version`. Worker в `docker-compose.yml` ждёт healthy backend. `prompt` снимает пробелы по краям ответа. `normalize_tz` заменяет `Moscow` на `Europe/Moscow`.

`alembic/env.py` takes `pg_advisory_xact_lock` before `CREATE TABLE alembic_version`. The worker in `docker-compose.yml` waits for a healthy backend. `prompt` trims the answer. `normalize_tz` replaces `Moscow` with `Europe/Moscow`.

## Аудит 3.1.3 / 3.1.3 audit

`prompt` при неинтерактивном stdin читает ответ с `/dev/tty`. `install.sh` перед `exec` тоже подключает `/dev/tty`, если это не `INSTALL_NONINTERACTIVE=1`.

When stdin is not a terminal, `prompt` reads the answer from `/dev/tty`. `install.sh` also attaches `/dev/tty` before `exec`, unless `INSTALL_NONINTERACTIVE=1`.

## Аудит 3.1.2 / 3.1.2 audit

`redact_remote` убирает поля с маркерами пароля, токена, подписки и протоколов из ответа Remnawave. `rw_subscription` и `rw_keys` требуют `users.keys`. `_public_audit_details` подменяет секретные ключи JSON на `unavailable`. `_public_refund_reason` отрезает хвост с текстом исключения. `admin_overview` считает строки через `func.count` и отдаёт только `response.total`.

`redact_remote` drops Remnawave fields whose names carry password, token, subscription, or protocol markers. `rw_subscription` and `rw_keys` require `users.keys`. `_public_audit_details` replaces secret JSON keys with `unavailable`. `_public_refund_reason` cuts the exception tail. `admin_overview` counts rows with `func.count` and returns only `response.total`.

## Аудит 3.1.1 / 3.1.1 audit

`update_staging_e2e_config` оставляет пустой секрет из предыдущей расшифрованной записи и заново сравнивает объединённые значения с production. `_redact_staging_output` заменяет секреты на `[скрыто]` до записи статуса. `_run_staging_e2e` считает прохождение по строке `FULL_E2E_PASS`.

`update_staging_e2e_config` keeps a blank secret from the previous decrypted record and compares the merged values with production again. `_redact_staging_output` replaces secrets with `[скрыто]` before the status is stored. `_run_staging_e2e` treats a pass as the line `FULL_E2E_PASS`.

## Аудит 3.1.0 / 3.1.0 audit

`plans` не кладёт `remnawave_profile_id` в публичный JSON. `auto_renew_status` подменяет текст ошибки фразой «Автопродление не выполнено». `upload_app_file` пишет `file_sha256`. `public_install_guide` собирает шаги установки. `subscription_file` отдаёт ссылку подписки как `text/plain`.

`plans` omits `remnawave_profile_id` from the public JSON. `auto_renew_status` replaces the error text with «Автопродление не выполнено». `upload_app_file` stores `file_sha256`. `public_install_guide` builds the install steps. `subscription_file` returns the subscription URL as `text/plain`.

## Аудит 3.0.1 / 3.0.1 audit

`decrypt_secret` расшифровывает токен автопродления и пароль копии. `wallet_spend` требует `Idempotency-Key` и отклоняет второе списание того же снимка тарифа в течение 30 секунд. Создание платежа под блокировкой `lock:checkout-intent` не открывает второй счёт, пока первый ещё не завершён.

`decrypt_secret` decrypts the auto-renew token and the backup password. `wallet_spend` requires `Idempotency-Key` and rejects a second debit of the same plan snapshot within 30 seconds. Payment creation under `lock:checkout-intent` does not open a second invoice while the first one is still open.

## Аудит 3.0.0-realise / 3.0.0-realise audit

`_request_body_limit` поднимает потолок только для `POST /api/admin/apps/{id}/file`. `_peer_is_trusted_proxy` решает, можно ли читать `X-Forwarded-For`. Исходящие клиенты с секретом используют `trust_env=False`. Повтор платежа возвращает «Повтор выдачи не выполнен», а не текст исключения. Пароль считается с `maxmem` 64 МиБ. Журнал аудита пишет `request_id` и сериализует Decimal. Флаг функции читается по колонке `key`.

`_request_body_limit` raises the ceiling only for `POST /api/admin/apps/{id}/file`. `_peer_is_trusted_proxy` decides whether `X-Forwarded-For` may be read. Outbound clients that carry a secret use `trust_env=False`. A payment retry returns «Повтор выдачи не выполнен» and does not return the exception text. Passwords are hashed with `maxmem` 64 MiB. The audit log stores `request_id` and serializes Decimal. A feature flag is read by the `key` column.

## Скачивание приложений / App downloads (2.13.0)

Администратор с правом `manage_content` загружает APK или IPA на карточку `POST /api/admin/apps/{id}/file`. Панель показывает ссылку администратора `GET /api/admin/apps/{id}/download`. Кабинет покупателя показывает ссылку `GET /api/public/apps/{id}/download` только для включённых карточек `android-user` и `ios-user`. Имя файла на диске в JSON не попадает. Каталог `app-packages` лежит рядом с `MEDIA_DIR` и входит в резервную копию.

An administrator with `manage_content` uploads an APK or IPA with `POST /api/admin/apps/{id}/file`. The panel links to `GET /api/admin/apps/{id}/download` for the administrator app. The buyer cabinet links to `GET /api/public/apps/{id}/download` only for enabled `android-user` and `ios-user` cards. The stored file name is not returned in JSON. The `app-packages` directory sits next to `MEDIA_DIR` and is included in a backup.

## Рассылка Telegram / Telegram broadcast (2.12.0)

| Шаг | Где | Что происходит |
| --- | --- | --- |
| 1 | Панель «Маркетинг», Android/iOS администратора | Оператор с правом `manage_broadcasts` отправляет текст, аудиторию `all` / `active` / `inactive`, необязательные кнопку и картинку |
| 2 | `POST /api/admin/broadcasts` | Проверяет `BOT_TOKEN`, пару кнопки, длину подписи 1024 и публичный HTTPS. Пишет строку `queued` и аудит `marketing.broadcast.queued` |
| 3 | `broadcast_worker` в процессе бота | `FOR UPDATE SKIP LOCKED` переводит строку в `sending`, выбирает пользователей с `telegram_id` без повторов, шлёт `sendMessage` или `sendPhoto` |
| 4 | После каждого получателя | Сохраняет `sent_count` и `failed_count`. Ответ 429 повторяется один раз. Прокси окружения не используется |
| 5 | Сбой | Статус `failed`. `POST /api/admin/broadcasts/{id}/retry` возвращает `queued` и продолжает с `sent_count + failed_count` |
| 6 | Конец списка | Статус `completed`, заполняется `finished_at` |

| Step | Where | What happens |
| --- | --- | --- |
| 1 | Marketing panel, Android/iOS administrator app | An operator with `manage_broadcasts` sends text, audience `all` / `active` / `inactive`, and an optional button and image |
| 2 | `POST /api/admin/broadcasts` | Checks `BOT_TOKEN`, the button pair, the 1024-character caption and a public HTTPS URL. Inserts `queued` and audits `marketing.broadcast.queued` |
| 3 | `broadcast_worker` in the bot process | `FOR UPDATE SKIP LOCKED` moves the row to `sending`, selects distinct users with `telegram_id`, and calls `sendMessage` or `sendPhoto` |
| 4 | After each recipient | Saves `sent_count` and `failed_count`. HTTP 429 is retried once. Environment proxies are ignored |
| 5 | Failure | Status `failed`. `POST /api/admin/broadcasts/{id}/retry` returns `queued` and continues from `sent_count + failed_count` |
| 6 | End of the list | Status `completed` and `finished_at` is set |

Добавлено в 2.12.0: аудитория в панели, вкладка рассылки в приложениях администратора, продолжение с счётчика, статус `failed` после сбоя воркера, отказ от повторной отправки одному пользователю с несколькими подписками, лимит подписи и пара кнопки.

Added in 2.12.0: an audience control in the panel, a broadcast tab in the administrator apps, resume from the counter, status `failed` after a worker crash, one delivery per user when several subscriptions exist, the caption limit and the button pair.

Добавлено в 2.11.0: `scripts/update.sh` копирует `UPDATE_STAGE` только после tar-снимка и `pg_dump`. `scripts/github_release_fetch.py` отклоняет symlink, путь с `..` и архив больше 80 МБ. `README.md` содержит полную русскую и полную английскую части.

Added in 2.11.0: `scripts/update.sh` copies `UPDATE_STAGE` only after the tar snapshot and `pg_dump`. `scripts/github_release_fetch.py` rejects a symlink, a `..` path and an archive larger than 80 MB. `README.md` has a full Russian part and a full English part.

Добавлено в 2.10.0: HMAC клиента в `mobile_auth.py`, `GET /api/me/devices` без `device_key` и `last_ip`, `GET /api/me/traffic` с лимитом из снимка, sandbox в `POST /api/me/wallet/topup`, `notify_user_telegram` после пополнения и выдачи, `POST /api/admin/plans/{id}/enabled`, `GET /api/admin/payments/{id}` без текста ошибки, `stale` у агентов, `GET /api/admin/github-update` и скрипты `scripts/github_release_fetch.py` и `scripts/update-from-github.sh`. Release APK 2.10.0 подписаны отдельно от debug APK 2.9.0. IPA по-прежнему собирается в Xcode.

Added in 2.10.0: client HMAC, a device list without `device_key` and `last_ip`, traffic with the snapshot limit, sandbox wallet top-up, Telegram notices after top-up and fulfillment, plan enable, payment detail, stale agents, the GitHub update status route and the host update scripts. The 2.10.0 APKs are release-signed. The IPA is still built in Xcode.

Добавлено в 2.9.0: debug APK `remnawave_vpn_shop_android_user_2_9_0.apk` и `remnawave_vpn_shop_android_admin_2_9_0.apk`, скрипт `scripts/build-android-apk.sh`, User-Agent `2.9.0`, разбор платёжного URL в Android и видимость `localHttpHosts` для экрана оплаты iOS. IPA собирается в Xcode. Добавлено в 2.8.0: модуль `mobile_catalog.py`, маршруты `/api/public/apps` и `/api/admin/apps`, логотип `client_logo`, вкладка админки «Приложения» и блок приложений в личном кабинете. Добавлено в 2.7.0: `backend/app/mobile_auth.py`, каталоги `mobile/android-user`, `mobile/android-admin`, `mobile/ios-user`, `mobile/ios-admin`, общие правила `mobile/client_rules.py`, выдача `access_token` только для заголовка `X-Shop-Client`, английские тексты `connection-info` по `Accept-Language`. Добавлено в 2.6.0: модули `abuse.py` и `platform_api.py`, миграция `0038_v2_6_0_platform`, агент `scripts/node-agent.py`, ограничение `users.restricted_at`, чёрный список HWID, ключи API, подписанные webhook, SMTP и DKIM, команда бота `/ops`, темы админки и манифест кабинета. Добавлено в 2.5.0: модуль `tariff_api.py`, модели `TariffConstructor` и `TariffConstructorOption`, миграция `0037_v2_5_0_tariff_constructor`, расчёт `quote_constructor` в оплате и списании кошелька, очищенный статус узлов Remnawave для админки, кабинета и Mini App. Добавлено в 2.4.0: модуль `cabinet_api.py` (email/VK auth, CMS меню кабинета, sandbox complete), `SandboxProvider`, `CabinetMenuItem`, SPA `cabinet/`, админ CMS «Личный кабинет», `scripts/sandbox-e2e.sh`. Добавлено в 2.3.0: `ensure_required_channel`, `wallet_topup`, `wallet_spend`, `purchase_gift`, промокод вида `days`, автопродление за `AUTO_RENEW_LEAD_DAYS` дней, deep-link подарка в боте.

## Архитектура

Запрос проходит путь Browser или Telegram → Caddy → FastAPI (`backend/app/main.py` + `cabinet_api.py` + `tariff_api.py` + `platform_api.py`) → PostgreSQL и Redis. Выдача VPN идёт в Remnawave. Платежи подтверждаются у провайдера, не по тексту вебхука. Фоновые циклы живут в API-процессе и в `backend/worker.py`. Агент узла ходит в API отдельно, с заголовком `X-Agent-Token`.

Админка (`admin/src/main.tsx`), Mini App (`miniapp/src/main.tsx`) и личный кабинет (`cabinet/src/main.tsx`) ходят в API с cookie-сессией и заголовком `X-CSRF-Token`. Приложения Android и iOS ходят с `Authorization: Bearer` и заголовком `X-Shop-Client` и cookie не сохраняют.

## Критические потоки

1. **Вход администратора.** `admin_login` проверяет пароль, при включённой 2FA — TOTP или код восстановления, выпускает JWT с `jti` и пишет `AdminSession`. `current_admin` отклоняет токен без сессии, чужой User-Agent и простой дольше 15 минут.
2. **Вход покупателя.** Telegram initData проверяется HMAC. Email+пароль, VK ID и Yandex ID опциональны (включаются переменными окружения). Сессия покупателя — HttpOnly cookie `rw_user`.
3. **Оплата.** `create_payment` сначала записывает намерение в БД, затем вызывает `Provider.create`. При `PAYMENTS_SANDBOX=true` доступен провайдер `sandbox` без живых шлюзов. Вебхук YooKassa принимается только с IP из allowlist. До выдачи `verify_succeeded` сверяет сумму, валюту и `order_id`.
4. **Выдача.** `fulfill` под блокировкой пользователя и платежа создаёт или продлевает пользователя Remnawave. Повтор той же операции не продлевает подписку второй раз.
5. **Возврат.** `execute_refund` вызывает `Provider.refund`. После подтверждённого возврата доступ в Remnawave отзывается, если нет более новой оплаченной выдачи. Реферальное начисление сторнируется.
6. **Удаление аккаунта.** `privacy_delete` и выдача делят user-lock, чтобы пробный период и автопродление не создали доступ после удаления.
7. **Резервная копия.** Архив пишется в `BACKUPS_DIR`. Восстановление требует подтверждения и, если включена 2FA, одноразовый код. Неуспешный restore оставляет технический режим.

## Critical flows (English)

1. Admin login checks the password and, when enabled, TOTP or a recovery code, then stores a session bound to the user agent.
2. Buyers sign in with verified Telegram initData. Yandex ID stays disabled until its three environment variables are set.
3. A payment intent is stored before the provider call. A YooKassa webhook is rejected when the IP allowlist is empty or does not match. Fulfillment waits for amount, currency and order id confirmation.
4. Fulfillment creates or extends the Remnawave user under a user lock and a payment lock.
5. A refund revokes access only when no newer fulfilled payment still entitles the customer, and it reverses the referral reward.
6. Account deletion shares the user lock with trial provisioning and auto-renew.
7. Backups live in `BACKUPS_DIR`. A failed restore leaves maintenance mode on.

## Функции интерфейса

| Функция | Где | Что делает |
| --- | --- | --- |
| `t` | admin/src/i18n.tsx, miniapp/src/i18n.tsx | Переводит точную русскую строку на английский, если выбран язык `en`. |
| `translate` | те же файлы | Чистая функция перевода, включая шаблоны «Активна до …» и «N записей». |
| `LangProvider` / `useLang` | те же файлы | Хранит язык в `localStorage` ключ `rw_lang` и в `document.documentElement.lang`. |
| `DomLocalizer` | те же файлы | После отрисовки заменяет текстовые узлы, placeholder, title и aria-label. |
| `detectLang` | те же файлы | Берёт сохранённый язык, иначе язык сервера или браузера. |
| `req` | admin и miniapp main.tsx | `fetch` с cookie, JSON и CSRF для не-GET запросов. |
| `csrf` | те же файлы | Читает cookie `rw_csrf`. |
| `Вход` | admin | Форма входа: email, пароль, необязательный TOTP, Telegram WebApp. |
| `App` | admin | Каркас панели: сессия, вкладки, тема, язык. |
| `Content` и экраны вкладок | admin | Загружают свой `/api/admin/...` и показывают таблицы и формы. |
| `App` | miniapp | Кабинет: подписка, тарифы, промокод, рефералы, поддержка, подарок, отзыв сессий. |
| `ShopApi` / `ShopClient` | mobile | HTTP без редиректов, Bearer, `X-Shop-Client`, стабильный User-Agent. |
| `normalizeBase` / `publicNode` | mobile | Проверка адреса API и повторная очистка узла на клиенте. |

## Backend

### Конфигурация

Файл: `backend/app/config.py`.

| Строка | Вид | Имя | Контракт | Назначение |
| --- | --- | --- | --- | --- |
| 15 | class | `Settings` | `` | Настройки приложения. |
| 241 | def | `Settings._normalize_cors` | `` | Убираем пробелы и пустые элементы. |
| 249 | def | `Settings.admin_cors_origins_list` | `` | Вернуть список origin'ов для CORS middleware. |

### База данных

Файл: `backend/app/db.py`.

| Строка | Вид | Имя | Контракт | Назначение |
| --- | --- | --- | --- | --- |
| 8 | class | `Base` | ` | Операция «Base». |
| 11 | async | `get_db` | ` | Операция «get db». |

### Безопасность

Файл: `backend/app/security.py`.

| Строка | Вид | Имя | Контракт | Назначение |
| --- | --- | --- | --- | --- |
| 25 | def | `_key` | ` | Операция «key». |
| 29 | def | `hash_password` | `` | Хеширует пароль scrypt и возвращает строку для хранения. |
| 36 | def | `verify_password` | `` | Сравнивает пароль с scrypt-хешем в постоянном времени. |
| 47 | def | `encrypt_secret` | `` | Шифрует секрет AES-GCM ключом от APP_SECRET. |
| 53 | def | `decrypt_secret` | `` | Расшифровывает секрет текущим или предыдущим APP_SECRET. |
| 63 | def | `issue_token` | `` | Выпускает JWT администратора. |
| 72 | def | `decode_token` | `` | Проверяет JWT администратора и срок действия. |
| 84 | async | `revoke_all_admin_sessions` | ` | Операция «revoke all admin sessions». |
| 87 | async | `current_admin` | `` | Достаёт администратора из cookie или Bearer и проверяет сессию. |
| 135 | def | `require_permission` | `` | Зависимость FastAPI: пускает только роль с указанным правом. |
| 143 | def | `verify_totp` | `` | Проверяет TOTP-код администратора. |
| 152 | def | `generate_recovery_codes` | `` | Генерирует одноразовые коды восстановления 2FA. |
| 156 | def | `set_recovery_codes` | `` | Сохраняет коды восстановления в зашифрованном виде. |
| 160 | def | `consume_recovery_code` | `` | Принимает и гасит один код восстановления. |

### TOTP

Файл: `backend/app/totp.py`.

| Строка | Вид | Имя | Контракт | Назначение |
| --- | --- | --- | --- | --- |
| 3 | def | `random_base32` | `` | Генерирует секрет TOTP. |
| 6 | def | `code` | ` | Операция «code». |
| 15 | def | `verify` | `` | Проверяет TOTP с окном допуска. |
| 20 | def | `provisioning_uri` | `` | Строит otpauth URI для приложения-аутентификатора. |

### Платежи

Файл: `backend/app/payments.py`.

| Строка | Вид | Имя | Контракт | Назначение |
| --- | --- | --- | --- | --- |
| 35 | def | `_public_client` | `` | Исходящие запросы к платёжным API идут только через DNS-pinned клиент. |
| 41 | def | `_money` | ` | Форматирует сумму до двух знаков после запятой. |
| 45 | def | `_checkout` | ` | Приводит ответ провайдера к полям id, url и status. |
| 56 | class | `PaymentError` | `` | Базовое исключение для ошибок платежных систем. |
| 60 | class | `SignatureVerificationError` | `` | Ошибка проверки вебхука (подпись или IP). |
| 64 | class | `WebhookReplayError` | `` | Ошибка повторного использования вебхука (replay attack). |
| 68 | class | `WebhookAlreadyProcessedError` | `` | Вебхук с таким event_id уже был обработан. |
| 76 | class | `BasePaymentProvider` | `` | Абстрактный базовый класс для платежных провайдеров. |
| 79 | def | `BasePaymentProvider.__init__` | ` | Операция «init». |
| 82 | async | `BasePaymentProvider._get_client` | `` | Клиент с фиксацией DNS. Нельзя открывать прямой httpx.AsyncClient. |
| 88 | async | `BasePaymentProvider.close` | `` | Закрыть HTTP-клиент. |
| 94 | async | `BasePaymentProvider.create_payment` | `` | Создать платеж. |
| 105 | async | `BasePaymentProvider.get_payment_status` | `` | Получить статус платежа. |
| 110 | def | `BasePaymentProvider.verify_webhook` | `` | Проверить вебхук и вернуть его данные. |
| 124 | class | `YooKassaProvider` | `` | Провайдер YooKassa. |
| 132 | def | `YooKassaProvider.__init__` | ` | Операция «init». |
| 137 | async | `YooKassaProvider.create_payment` | ` | Операция «create payment». |
| 189 | async | `YooKassaProvider.get_payment_status` | ` | Читает статус платежа и возвращает строку статуса. |
| 199 | async | `YooKassaProvider.refund_payment` | ` | Операция «refund payment». |
| 216 | def | `YooKassaProvider._verify_ip` | `` | Проверить IP-адрес отправителя по allowlist. Пустой список отклоняет вебхук. |
| 241 | def | `YooKassaProvider.verify_webhook` | `` | Проверить вебхук YooKassa: |
| 274 | def | `YooKassaProvider._cleanup_old_events` | `` | Удалить старые записи из кэша обработанных событий. |
| 285 | async | `YooKassaProvider.create` | ` | Создаёт платёж и возвращает id и ссылку оплаты. |
| 289 | async | `YooKassaProvider.charge_recurring` | `` | Повторное списание сохранённым способом оплаты. Idempotence-Key = order_id. |
| 308 | async | `YooKassaProvider.verify_succeeded` | ` | Сверяет у провайдера статус succeeded, сумму, валюту и order_id. |
| 325 | async | `YooKassaProvider.find_by_order_id` | ` | Ищет платёж YooKassa по metadata.order_id. |
| 338 | async | `YooKassaProvider.refund` | ` | Запрашивает возврат у провайдера с идемпотентным ключом refund-{payment_id}. |
| 351 | async | `YooKassaProvider.get_refund_status` | ` | Читает статус возврата у провайдера. |
| 365 | class | `PlategaProvider` | `` | Провайдер Platega. |
| 368 | def | `PlategaProvider.__init__` | ` | Операция «init». |
| 371 | async | `PlategaProvider.create_payment` | ` | Операция «create payment». |
| 401 | async | `PlategaProvider.get_payment_status` | ` | Читает статус платежа и возвращает строку статуса. |
| 414 | async | `PlategaProvider.create` | ` | Создаёт платёж и возвращает id и ссылку оплаты. |
| 418 | async | `PlategaProvider.verify_succeeded` | ` | Сверяет у провайдера статус succeeded, сумму, валюту и order_id. |
| 434 | async | `PlategaProvider.refund` | ` | Запрашивает возврат у провайдера с идемпотентным ключом refund-{payment_id}. |
| 448 | async | `PlategaProvider.get_refund_status` | ` | Читает статус возврата у провайдера. |
| 458 | def | `PlategaProvider.verify_webhook` | `` | Проверка подписи вебхука Platega (HMAC-SHA256). |
| 493 | class | `RollyPayProvider` | `` | Провайдер RollyPay. |
| 496 | def | `RollyPayProvider.__init__` | ` | Операция «init». |
| 499 | async | `RollyPayProvider.create_payment` | ` | Операция «create payment». |
| 529 | async | `RollyPayProvider.get_payment_status` | ` | Читает статус платежа и возвращает строку статуса. |
| 541 | async | `RollyPayProvider.create` | ` | Создаёт платёж и возвращает id и ссылку оплаты. |
| 545 | async | `RollyPayProvider.verify_succeeded` | ` | Сверяет у провайдера статус succeeded, сумму, валюту и order_id. |
| 561 | async | `RollyPayProvider.refund` | ` | Запрашивает возврат у провайдера с идемпотентным ключом refund-{payment_id}. |
| 578 | async | `RollyPayProvider.get_refund_status` | ` | Читает статус возврата у провайдера. |
| 587 | def | `RollyPayProvider.verify_webhook` | `` | Проверка подписи вебхука RollyPay (HMAC-SHA256) + timestamp. |
| 647 | def | `get_payment_provider` | `` | Вернуть singleton-провайдер по имени. |
| 661 | async | `close_all_providers` | `` | Закрыть HTTP-клиенты всех провайдеров при остановке. |
| 667 | def | `verify_platega_headers` | ` | Сверяет заголовки Platega с секретом магазина. |
| 673 | def | `verify_rollypay` | ` | Проверяет HMAC и окно timestamp 5 минут. |
| 686 | async | `staging_create_payment` | `` | Создать платёж только по переданным staging credentials. |

### Remnawave

Файл: `backend/app/remnawave.py`.

| Строка | Вид | Имя | Контракт | Назначение |
| --- | --- | --- | --- | --- |
| 9 | class | `RemnawaveError` | ` | Операция «RemnawaveError». |
| 12 | class | `RemnawaveCircuitOpen` | ` | Операция «RemnawaveCircuitOpen». |
| 15 | class | `RemnawaveClient` | ` | Операция «RemnawaveClient». |
| 19 | def | `RemnawaveClient.__init__` | ` | Операция «init». |
| 28 | async | `RemnawaveClient._get_shared_client` | ` | Операция «get shared client». |
| 42 | async | `RemnawaveClient.close_shared_client` | ` | Операция «close shared client». |
| 47 | async | `RemnawaveClient._request` | ` | Операция «request». |
| 77 | async | `RemnawaveClient.get_user` | ` | Операция «get user». |
| 80 | async | `RemnawaveClient.get_user_by_username` | ` | Операция «get user by username». |
| 83 | async | `RemnawaveClient.stream_users` | ` | Операция «stream users». |
| 90 | async | `RemnawaveClient.list_users` | ` | Операция «list users». |
| 94 | async | `RemnawaveClient.create_user` | ` | Операция «create user». |
| 110 | async | `RemnawaveClient.get_expiry` | ` | Операция «get expiry». |
| 120 | async | `RemnawaveClient.extend_idempotent` | ` | Операция «extend idempotent». |
| 136 | async | `RemnawaveClient.patch_user` | ` | Операция «patch user». |
| 140 | async | `RemnawaveClient.extend_user` | ` | Операция «extend user». |
| 144 | async | `RemnawaveClient.update_entitlements` | ` | Операция «update entitlements». |
| 153 | async | `RemnawaveClient.disable_user` | ` | Операция «disable user». |
| 156 | async | `RemnawaveClient.enable_user` | ` | Операция «enable user». |
| 159 | async | `RemnawaveClient.reset_traffic` | ` | Операция «reset traffic». |
| 162 | async | `RemnawaveClient.get_subscription` | ` | Операция «get subscription». |
| 165 | async | `RemnawaveClient.get_connection_keys` | ` | Операция «get connection keys». |
| 168 | async | `RemnawaveClient.accessible_nodes` | ` | Операция «accessible nodes». |
| 171 | async | `RemnawaveClient.list_nodes` | ` | Операция «list nodes». |

### Провижининг узлов

Файл: `backend/app/provisioner.py`.

| Строка | Вид | Имя | Контракт | Назначение |
| --- | --- | --- | --- | --- |
| 4 | class | `ProvisionError` | ` | Операция «ProvisionError». |
| 7 | class | `_FingerprintPolicy` | ` | Операция «FingerprintPolicy». |
| 8 | def | `_FingerprintPolicy.__init__` | ` | Операция «init». |
| 9 | def | `_FingerprintPolicy.missing_host_key` | ` | Операция «missing host key». |
| 15 | def | `hmac_compare` | ` | Операция «hmac compare». |
| 19 | def | `_connect` | ` | Операция «connect». |
| 35 | def | `run_ssh` | ` | Операция «run ssh». |

### Telegram-бот

Файл: `backend/app/bot.py`.

| Строка | Вид | Имя | Контракт | Назначение |
| --- | --- | --- | --- | --- |
| 34 | def | `_lang` | ` | Операция «lang». |
| 41 | def | `_tr` | ` | Операция «tr». |
| 48 | async | `get_bot_config` | ` | Операция «get bot config». |
| 61 | def | `promo_text` | ` | Операция «promo text». |
| 70 | async | `broadcast_worker` | ` | Операция «broadcast worker». |
| 109 | async | `start` | `router.message(CommandStart())` | HTTP handler router.message(CommandStart()) |
| 154 | async | `promo` | `router.message(Command("promo"))` | HTTP handler router.message(Command("promo")) |
| 165 | async | `main` | ` | Операция «main». |

### HTTP API и бизнес-логика

Файл: `backend/app/main.py`.

| Строка | Вид | Имя | Контракт | Назначение |
| --- | --- | --- | --- | --- |
| 67 | def | `_track_task` | ` | Операция «track task». |
| 73 | async | `_redis_allowed` | ` | Операция «redis allowed». |
| 86 | def | `_client_ip` | ` | Операция «client ip». |
| 100 | def | `_csrf_cookie_value` | ` | Операция «csrf cookie value». |
| 103 | def | `_require_csrf` | ` | Операция «require csrf». |
| 113 | def | `_set_auth_cookies` | ` | Операция «set auth cookies». |
| 118 | class | `SecurityHeadersMiddleware` | ` | Операция «SecurityHeadersMiddleware». |
| 119 | async | `SecurityHeadersMiddleware.dispatch` | ` | Операция «dispatch». |
| 130 | async | `SecurityHeadersMiddleware._dispatch` | ` | Операция «dispatch». |
| 197 | class | `LoginIn` | ` | Операция «LoginIn». |
| 202 | class | `OtpIn` | ` | Операция «OtpIn». |
| 204 | class | `PlanIn` | ` | Операция «PlanIn». |
| 213 | class | `TicketIn` | ` | Операция «TicketIn». |
| 217 | class | `WithdrawalIn` | ` | Операция «WithdrawalIn». |
| 221 | class | `IncidentIn` | ` | Операция «IncidentIn». |
| 226 | class | `SecretRotateIn` | ` | Операция «SecretRotateIn». |
| 229 | class | `RefundIn` | ` | Операция «RefundIn». |
| 233 | class | `SubscriptionActionIn` | ` | Операция «SubscriptionActionIn». |
| 236 | class | `GiftRedeemIn` | ` | Операция «GiftRedeemIn». |
| 239 | class | `GiftCreateIn` | ` | Операция «GiftCreateIn». |
| 246 | class | `AdminTicketReplyIn` | ` | Операция «AdminTicketReplyIn». |
| 249 | class | `WithdrawalActionIn` | ` | Операция «WithdrawalActionIn». |
| 252 | class | `FraudDecisionIn` | ` | Операция «FraudDecisionIn». |
| 257 | class | `NotificationIn` | ` | Операция «NotificationIn». |
| 265 | class | `StatusComponentIn` | ` | Операция «StatusComponentIn». |
| 273 | class | `DeploymentIn` | ` | Операция «DeploymentIn». |
| 279 | class | `DeploymentPromoteIn` | ` | Операция «DeploymentPromoteIn». |
| 286 | async | `audit` | ` | Операция «audit». |
| 289 | async | `record_financial_event` | `` | Append an immutable financial event exactly once. |
| 303 | async | `enqueue_notification` | ` | Операция «enqueue notification». |
| 311 | async | `maintenance_enabled` | ` | Операция «maintenance enabled». |
| 316 | def | `_maintenance_response` | ` | Операция «maintenance response». |
| 321 | async | `startup` | `app.on_event("startup")` | HTTP handler app.on_event("startup") |
| 339 | async | `shutdown_resources` | `app.on_event("shutdown")` | HTTP handler app.on_event("shutdown") |
| 358 | async | `start_backup_scheduler` | `app.on_event("startup")` | HTTP handler app.on_event("startup") |
| 370 | async | `health_live` | `app.get("/health/live")` | HTTP handler app.get("/health/live") |
| 374 | async | `health_ready` | `app.get("/health/ready")` | HTTP handler app.get("/health/ready") |
| 381 | async | `health` | `app.get("/health")` | HTTP handler app.get("/health") |
| 393 | async | `send_alert` | ` | Операция «send alert». |
| 414 | async | `metrics_middleware` | `app.middleware("http")` | HTTP handler app.middleware("http") |
| 426 | async | `metrics` | `app.get("/metrics")` | HTTP handler app.get("/metrics") |
| 434 | def | `telegram_user_from_init_data` | ` | Проверяет подпись Telegram initData и читает пользователя. |
| 456 | async | `telegram_auth` | `app.post("/api/auth/telegram")` | HTTP handler app.post("/api/auth/telegram") |
| 472 | def | `issue_user_token` | ` | Операция «issue user token». |
| 477 | async | `create_user_session` | ` | Операция «create user session». |
| 483 | async | `user_from_token` | ` | Операция «user from token». |
| 506 | async | `user_logout` | `app.post("/api/auth/logout")` | HTTP handler app.post("/api/auth/logout") |
| 517 | async | `revoke_all_user_sessions` | `app.post("/api/me/security/revoke-all")` | HTTP handler app.post("/api/me/security/revoke-all") |
| 524 | async | `yandex_login` | `app.get("/api/auth/yandex")` | HTTP handler app.get("/api/auth/yandex") |
| 535 | async | `yandex_callback` | `app.get("/api/auth/yandex/callback")` | HTTP handler app.get("/api/auth/yandex/callback") |
| 564 | class | `ExchangeIn` | ` | Операция «ExchangeIn». |
| 568 | async | `auth_exchange` | `app.post("/api/auth/exchange")` | HTTP handler app.post("/api/auth/exchange") |
| 578 | async | `active_promotion` | ` | Операция «active promotion». |
| 588 | def | `discounted_amount` | ` | Операция «discounted amount». |
| 594 | async | `promo_discount` | ` | Операция «promo discount». |
| 617 | async | `my_devices` | `app.get("/api/me/devices")` | HTTP handler app.get("/api/me/devices") |
| 623 | async | `register_device` | `app.post("/api/me/devices")` | HTTP handler app.post("/api/me/devices") |
| 644 | async | `revoke_device` | `app.post("/api/me/devices/{device_id}/revoke")` | HTTP handler app.post("/api/me/devices/{device_id}/revoke") |
| 650 | async | `claim_trial` | `app.post("/api/me/trial")` | HTTP handler app.post("/api/me/trial") |
| 669 | async | `public_config` | `app.get("/api/public/config")` | HTTP handler app.get("/api/public/config") |
| 691 | async | `api_me` | `app.get("/api/me")` | HTTP handler app.get("/api/me") |
| 696 | async | `plans` | `app.get("/api/plans")` | HTTP handler app.get("/api/plans") |
| 706 | async | `validate_promo` | `app.get("/api/promo/validate")` | HTTP handler app.get("/api/promo/validate") |
| 712 | class | `DeviceRegisterIn` | ` | Операция «DeviceRegisterIn». |
| 717 | class | `CampaignIn` | ` | Операция «CampaignIn». |
| 726 | class | `RuleIn` | ` | Операция «RuleIn». |
| 734 | class | `MonitoringCheckIn` | ` | Операция «MonitoringCheckIn». |
| 742 | class | `TrialIn` | ` | Операция «TrialIn». |
| 748 | async | `admin_telegram_login` | `app.post("/api/admin/auth/telegram")` | HTTP handler app.post("/api/admin/auth/telegram") |
| 761 | async | `admin_login` | `app.post("/api/admin/auth/login")` | HTTP handler app.post("/api/admin/auth/login") |
| 791 | async | `mfa_setup` | `app.post("/api/admin/auth/mfa/setup")` | HTTP handler app.post("/api/admin/auth/mfa/setup") |
| 797 | async | `mfa_enable` | `app.post("/api/admin/auth/mfa/enable")` | HTTP handler app.post("/api/admin/auth/mfa/enable") |
| 803 | class | `PasswordConfirm` | ` | Операция «PasswordConfirm». |
| 807 | async | `mfa_disable` | `app.post("/api/admin/auth/mfa/disable")` | HTTP handler app.post("/api/admin/auth/mfa/disable") |
| 814 | async | `mfa_status` | `app.get("/api/admin/auth/mfa/status")` | HTTP handler app.get("/api/admin/auth/mfa/status") |
| 817 | async | `feature_enabled` | ` | Операция «feature enabled». |
| 822 | async | `_payment_provider_order` | ` | Операция «payment provider order». |
| 863 | async | `reserve_promo` | ` | Операция «reserve promo». |
| 876 | async | `release_promo_reservation` | ` | Операция «release promo reservation». |
| 887 | async | `create_payment` | `app.post("/api/payments/create")` | HTTP handler app.post("/api/payments/create") |
| 1021 | async | `_renew_redis_lock` | ` | Операция «renew redis lock». |
| 1044 | async | `_acquire_redis_lock` | ` | Операция «acquire redis lock». |
| 1054 | async | `_acquire_payment_side_effect_lock` | ` | Операция «acquire payment side effect lock». |
| 1061 | async | `_release_payment_side_effect_lock` | ` | Операция «release payment side effect lock». |
| 1072 | async | `_acquire_user_fulfillment_lock` | ` | Операция «acquire user fulfillment lock». |
| 1079 | async | `_confirm_and_fulfill_payment` | `` | Confirm a provider-successful payment without ever reviving a refunded payment. |
| 1119 | async | `fulfill` | ` | Выдаёт или продлевает подписку Remnawave после подтверждённой оплаты. |
| 1311 | async | `payment_by_provider` | ` | Операция «payment by provider». |
| 1314 | async | `payment_by_provider_or_order` | ` | Операция «payment by provider or order». |
| 1320 | async | `bind_provider_payment_id` | ` | Операция «bind provider payment id». |
| 1329 | def | `_ip_allowed` | ` | Операция «ip allowed». |
| 1339 | async | `register_provider_event` | `` | Atomically claim a verified event. Failed/retry events may be reclaimed; processed events are immutable. |
| 1353 | async | `finish_provider_event` | ` | Операция «finish provider event». |
| 1358 | async | `yookassa_webhook` | `app.post("/api/webhooks/yookassa")` | HTTP handler app.post("/api/webhooks/yookassa") |
| 1393 | async | `platega_webhook` | `app.post("/api/webhooks/platega")` | HTTP handler app.post("/api/webhooks/platega") |
| 1423 | async | `rollypay_webhook` | `app.post("/api/webhooks/rollypay")` | HTTP handler app.post("/api/webhooks/rollypay") |
| 1453 | async | `fulfillment_retry_scheduler` | ` | Операция «fulfillment retry scheduler». |
| 1465 | async | `refund_revoke_scheduler` | ` | Операция «refund revoke scheduler». |
| 1537 | async | `auto_renew_scheduler` | ` | Операция «auto renew scheduler». |
| 1670 | async | `reconciliation_scheduler` | ` | Операция «reconciliation scheduler». |
| 1703 | async | `subscription_lifecycle_scheduler` | ` | Операция «subscription lifecycle scheduler». |
| 1746 | async | `expiry_notification_scheduler` | ` | Операция «expiry notification scheduler». |
| 1777 | async | `my_subscription` | `app.get("/api/me/subscription")` | HTTP handler app.get("/api/me/subscription") |
| 1782 | async | `billing_center` | `app.get("/api/me/billing-center")` | HTTP handler app.get("/api/me/billing-center") |
| 1789 | async | `security_center` | `app.get("/api/me/security-center")` | HTTP handler app.get("/api/me/security-center") |
| 1797 | async | `subscription_lifecycle` | `app.post("/api/me/subscription/lifecycle")` | HTTP handler app.post("/api/me/subscription/lifecycle") |
| 1817 | async | `redeem_gift` | `app.post("/api/me/gifts/redeem")` | HTTP handler app.post("/api/me/gifts/redeem") |
| 1895 | async | `apply_referral` | `app.post("/api/me/referral/apply")` | HTTP handler app.post("/api/me/referral/apply") |
| 1905 | async | `auto_renew_status` | `app.get("/api/me/auto-renew")` | HTTP handler app.get("/api/me/auto-renew") |
| 1910 | async | `connection_qr` | `app.get("/api/me/connection-qr")` | HTTP handler app.get("/api/me/connection-qr") |
| 1918 | async | `connection_info` | `app.get("/api/me/connection-info")` | HTTP handler app.get("/api/me/connection-info") |
| 1924 | async | `set_auto_renew` | `app.put("/api/me/auto-renew")` | HTTP handler app.put("/api/me/auto-renew") |
| 1931 | async | `remove_auto_renew_method` | `app.delete("/api/me/auto-renew/method")` | HTTP handler app.delete("/api/me/auto-renew/method") |
| 1937 | async | `my_payments` | `app.get("/api/me/payments")` | HTTP handler app.get("/api/me/payments") |
| 1942 | async | `my_referral_ledger` | `app.get("/api/me/referral/ledger")` | HTTP handler app.get("/api/me/referral/ledger") |
| 1947 | async | `my_referral` | `app.get("/api/me/referral")` | HTTP handler app.get("/api/me/referral") |
| 1954 | async | `create_support_ticket` | `app.post("/api/me/support/tickets")` | HTTP handler app.post("/api/me/support/tickets") |
| 1961 | async | `my_support_tickets` | `app.get("/api/me/support/tickets")` | HTTP handler app.get("/api/me/support/tickets") |
| 1967 | async | `request_withdrawal` | `app.post("/api/me/referral/withdrawals")` | HTTP handler app.post("/api/me/referral/withdrawals") |
| 1982 | async | `my_withdrawals` | `app.get("/api/me/referral/withdrawals")` | HTTP handler app.get("/api/me/referral/withdrawals") |
| 1988 | async | `customer_dashboard` | `app.get("/api/me/dashboard")` | HTTP handler app.get("/api/me/dashboard") |
| 1997 | async | `my_notifications` | `app.get("/api/me/notifications")` | HTTP handler app.get("/api/me/notifications") |
| 2005 | async | `read_notification` | `app.post("/api/me/notifications/{notification_id}/read")` | HTTP handler app.post("/api/me/notifications/{notification_id}/read") |
| 2012 | async | `public_status` | `app.get("/api/public/status")` | HTTP handler app.get("/api/public/status") |
| 2017 | async | `admin_notifications` | `app.get("/api/admin/notifications")` | HTTP handler app.get("/api/admin/notifications") |
| 2022 | async | `admin_notification_create` | `app.post("/api/admin/notifications")` | HTTP handler app.post("/api/admin/notifications") |
| 2028 | async | `admin_status_components` | `app.get("/api/admin/status/components")` | HTTP handler app.get("/api/admin/status/components") |
| 2033 | async | `admin_status_component_create` | `app.post("/api/admin/status/components")` | HTTP handler app.post("/api/admin/status/components") |
| 2038 | async | `admin_status_component_update` | `app.put("/api/admin/status/components/{component_id}")` | HTTP handler app.put("/api/admin/status/components/{component_id}") |
| 2047 | async | `deployment_create` | `app.post("/api/admin/deployments")` | HTTP handler app.post("/api/admin/deployments") |
| 2054 | async | `deployment_promote` | `app.post("/api/admin/deployments/{deployment_id}/promote")` | HTTP handler app.post("/api/admin/deployments/{deployment_id}/promote") |
| 2064 | async | `deployment_rollback` | `app.post("/api/admin/deployments/{deployment_id}/rollback")` | HTTP handler app.post("/api/admin/deployments/{deployment_id}/rollback") |
| 2071 | async | `deployment_list` | `app.get("/api/admin/deployments")` | HTTP handler app.get("/api/admin/deployments") |
| 2077 | async | `recovery_operations` | `app.get("/api/admin/recovery/operations")` | HTTP handler app.get("/api/admin/recovery/operations") |
| 2082 | async | `retry_operation` | `app.post("/api/admin/recovery/operations/{operation_id}/retry")` | HTTP handler app.post("/api/admin/recovery/operations/{operation_id}/retry") |
| 2091 | async | `admin_refunds` | `app.get("/api/admin/refunds")` | HTTP handler app.get("/api/admin/refunds") |
| 2096 | async | `request_refund` | `app.post("/api/admin/payments/{payment_id}/refund-request")` | HTTP handler app.post("/api/admin/payments/{payment_id}/refund-request") |
| 2108 | async | `approve_refund` | `app.post("/api/admin/refunds/{refund_id}/approve")` | HTTP handler app.post("/api/admin/refunds/{refund_id}/approve") |
| 2115 | async | `_reverse_referral_reward_for_refund` | `` | Claw back a referral reward exactly once when its payment is refunded. |
| 2133 | async | `_safe_revoke_for_refunded_payment` | `` | Revoke only when no later successfully fulfilled purchase protects the subscription. |
| 2151 | async | `execute_refund` | `app.post("/api/admin/refunds/{refund_id}/execute")` | HTTP handler app.post("/api/admin/refunds/{refund_id}/execute") |
| 2207 | async | `retry_refund_revoke` | `app.post("/api/admin/refunds/{refund_id}/retry-revoke")` | HTTP handler app.post("/api/admin/refunds/{refund_id}/retry-revoke") |
| 2233 | async | `mark_refunded` | `app.post("/api/admin/refunds/{refund_id}/mark-refunded")` | HTTP handler app.post("/api/admin/refunds/{refund_id}/mark-refunded") |
| 2237 | async | `admin_tickets` | `app.get("/api/admin/support/tickets")` | HTTP handler app.get("/api/admin/support/tickets") |
| 2242 | async | `admin_ticket_reply` | `app.post("/api/admin/support/tickets/{ticket_id}/reply")` | HTTP handler app.post("/api/admin/support/tickets/{ticket_id}/reply") |
| 2249 | async | `admin_withdrawals` | `app.get("/api/admin/referrals/withdrawals")` | HTTP handler app.get("/api/admin/referrals/withdrawals") |
| 2254 | async | `reject_withdrawal` | `app.post("/api/admin/referrals/withdrawals/{withdrawal_id}/reject")` | HTTP handler app.post("/api/admin/referrals/withdrawals/{withdrawal_id}/reject") |
| 2274 | async | `approve_withdrawal` | `app.post("/api/admin/referrals/withdrawals/{withdrawal_id}/approve")` | HTTP handler app.post("/api/admin/referrals/withdrawals/{withdrawal_id}/approve") |
| 2284 | async | `paid_withdrawal` | `app.post("/api/admin/referrals/withdrawals/{withdrawal_id}/paid")` | HTTP handler app.post("/api/admin/referrals/withdrawals/{withdrawal_id}/paid") |
| 2293 | async | `admin_workers` | `app.get("/api/admin/workers")` | HTTP handler app.get("/api/admin/workers") |
| 2299 | async | `admin_releases` | `app.get("/api/admin/releases")` | HTTP handler app.get("/api/admin/releases") |
| 2304 | async | `check_release` | `app.post("/api/admin/releases/check")` | HTTP handler app.post("/api/admin/releases/check") |
| 2308 | async | `secret_status` | `app.get("/api/admin/security/secrets/status")` | HTTP handler app.get("/api/admin/security/secrets/status") |
| 2312 | async | `security_incident` | `app.post("/api/admin/security/incident")` | HTTP handler app.post("/api/admin/security/incident") |
| 2320 | async | `security_incidents` | `app.get("/api/admin/security/incidents")` | HTTP handler app.get("/api/admin/security/incidents") |
| 2325 | async | `admin_openapi` | `app.get("/api/admin/openapi.json")` | HTTP handler app.get("/api/admin/openapi.json") |
| 2329 | async | `admin_recovery` | `app.get("/api/admin/recovery")` | HTTP handler app.get("/api/admin/recovery") |
| 2339 | async | `incident_mode` | `app.post("/api/admin/incident-mode")` | HTTP handler app.post("/api/admin/incident-mode") |
| 2345 | async | `incident_mode_status` | `app.get("/api/admin/incident-mode")` | HTTP handler app.get("/api/admin/incident-mode") |
| 2349 | async | `reconcile_referrals` | `app.post("/api/admin/referrals/reconcile")` | HTTP handler app.post("/api/admin/referrals/reconcile") |
| 2358 | async | `system_health` | `app.get("/api/admin/system/health")` | HTTP handler app.get("/api/admin/system/health") |
| 2398 | async | `admin_analytics` | `app.get("/api/admin/analytics")` | HTTP handler app.get("/api/admin/analytics") |
| 2404 | async | `admin_sessions` | `app.get("/api/admin/sessions")` | HTTP handler app.get("/api/admin/sessions") |
| 2409 | async | `revoke_all_sessions` | `app.post("/api/admin/sessions/revoke-all")` | HTTP handler app.post("/api/admin/sessions/revoke-all") |
| 2417 | async | `revoke_admin_session` | `app.delete("/api/admin/sessions/{session_id}")` | HTTP handler app.delete("/api/admin/sessions/{session_id}") |
| 2423 | async | `reconcile_payments` | `app.post("/api/admin/payments/reconcile")` | HTTP handler app.post("/api/admin/payments/reconcile") |
| 2452 | async | `retry_payment` | `app.post("/api/admin/payments/{payment_id}/retry")` | HTTP handler app.post("/api/admin/payments/{payment_id}/retry") |
| 2465 | async | `my_traffic` | `app.get("/api/me/traffic")` | HTTP handler app.get("/api/me/traffic") |
| 2475 | async | `privacy_export` | `app.get("/api/me/privacy/export")` | HTTP handler app.get("/api/me/privacy/export") |
| 2484 | async | `privacy_delete` | `app.delete("/api/me/privacy/account")` | HTTP handler app.delete("/api/me/privacy/account") |
| 2524 | async | `admin_financial_ledger` | `app.get("/api/admin/financial-ledger")` | HTTP handler app.get("/api/admin/financial-ledger") |
| 2529 | async | `admin_monitoring` | `app.get("/api/admin/monitoring")` | HTTP handler app.get("/api/admin/monitoring") |
| 2536 | async | `admin_jobs` | `app.get("/api/admin/jobs")` | HTTP handler app.get("/api/admin/jobs") |
| 2541 | async | `retry_job` | `app.post("/api/admin/jobs/{job_id}/retry")` | HTTP handler app.post("/api/admin/jobs/{job_id}/retry") |
| 2547 | async | `admin_fraud` | `app.get("/api/admin/fraud")` | HTTP handler app.get("/api/admin/fraud") |
| 2552 | async | `fraud_decision` | `app.post("/api/admin/fraud/{signal_id}")` | HTTP handler app.post("/api/admin/fraud/{signal_id}") |
| 2559 | async | `fraud_scan` | `app.post("/api/admin/fraud/scan")` | HTTP handler app.post("/api/admin/fraud/scan") |
| 2571 | async | `admin_payouts` | `app.get("/api/admin/payouts")` | HTTP handler app.get("/api/admin/payouts") |
| 2576 | async | `admin_withdrawal_approve` | `app.post("/api/admin/ops/withdrawals/{withdrawal_id}/approve")` | HTTP handler app.post("/api/admin/ops/withdrawals/{withdrawal_id}/approve") |
| 2586 | async | `admin_withdrawal_paid` | `app.post("/api/admin/ops/withdrawals/{withdrawal_id}/paid")` | HTTP handler app.post("/api/admin/ops/withdrawals/{withdrawal_id}/paid") |
| 2594 | async | `reconcile_refund` | `app.post("/api/admin/refunds/{refund_id}/reconcile")` | HTTP handler app.post("/api/admin/refunds/{refund_id}/reconcile") |
| 2635 | async | `customer_360` | `app.get("/api/admin/customers/{user_id}/360")` | HTTP handler app.get("/api/admin/customers/{user_id}/360") |
| 2648 | async | `refund_dry_run` | `app.get("/api/admin/refunds/{refund_id}/dry-run")` | HTTP handler app.get("/api/admin/refunds/{refund_id}/dry-run") |
| 2662 | async | `risk_summary` | `app.get("/api/admin/security/risk-summary")` | HTTP handler app.get("/api/admin/security/risk-summary") |
| 2669 | async | `health_summary` | `app.get("/api/admin/health/summary")` | HTTP handler app.get("/api/admin/health/summary") |
| 2684 | async | `admin_gifts` | `app.get("/api/admin/gifts")` | HTTP handler app.get("/api/admin/gifts") |
| 2689 | async | `admin_gift_create` | `app.post("/api/admin/gifts")` | HTTP handler app.post("/api/admin/gifts") |
| 2699 | async | `admin_overview` | `app.get("/api/admin/overview")` | HTTP handler app.get("/api/admin/overview") |
| 2706 | async | `admin_list_plans` | `app.get("/api/admin/plans")` | HTTP handler app.get("/api/admin/plans") |
| 2711 | async | `create_plan` | `app.post("/api/admin/plans")` | HTTP handler app.post("/api/admin/plans") |
| 2715 | async | `admin_update_plan` | `app.put("/api/admin/plans/{plan_id}")` | HTTP handler app.put("/api/admin/plans/{plan_id}") |
| 2722 | async | `admin_delete_plan` | `app.delete("/api/admin/plans/{plan_id}")` | HTTP handler app.delete("/api/admin/plans/{plan_id}") |
| 2733 | async | `admin_payments` | `app.get("/api/admin/payments")` | HTTP handler app.get("/api/admin/payments") |
| 2739 | async | `admin_audit` | `app.get("/api/admin/audit")` | HTTP handler app.get("/api/admin/audit") |
| 2745 | async | `rw_users` | `app.get("/api/admin/remnawave/users")` | HTTP handler app.get("/api/admin/remnawave/users") |
| 2747 | async | `rw_user_stream` | `app.get("/api/admin/remnawave/users/stream")` | HTTP handler app.get("/api/admin/remnawave/users/stream") |
| 2749 | async | `rw_nodes` | `app.get("/api/admin/remnawave/nodes")` | HTTP handler app.get("/api/admin/remnawave/nodes") |
| 2751 | async | `rw_user` | `app.get("/api/admin/remnawave/users/{user_id}")` | HTTP handler app.get("/api/admin/remnawave/users/{user_id}") |
| 2753 | async | `rw_extend` | `app.post("/api/admin/remnawave/users/{user_id}/extend")` | HTTP handler app.post("/api/admin/remnawave/users/{user_id}/extend") |
| 2766 | async | `rw_subscription` | `app.get("/api/admin/remnawave/users/{user_id}/subscription")` | HTTP handler app.get("/api/admin/remnawave/users/{user_id}/subscription") |
| 2768 | async | `rw_keys` | `app.get("/api/admin/remnawave/users/{user_id}/keys")` | HTTP handler app.get("/api/admin/remnawave/users/{user_id}/keys") |
| 2771 | async | `remnawave_health` | `app.get("/api/admin/remnawave/health")` | HTTP handler app.get("/api/admin/remnawave/health") |
| 2779 | async | `provision_node` | `app.post("/api/admin/provision-node")` | HTTP handler app.post("/api/admin/provision-node") |
| 2788 | class | `AdminUserIn` | ` | Операция «AdminUserIn». |
| 2796 | async | `list_admins` | `app.get("/api/admin/admins")` | HTTP handler app.get("/api/admin/admins") |
| 2801 | async | `create_admin` | `app.post("/api/admin/admins")` | HTTP handler app.post("/api/admin/admins") |
| 2809 | async | `update_admin` | `app.put("/api/admin/admins/{admin_id}")` | HTTP handler app.put("/api/admin/admins/{admin_id}") |
| 2821 | async | `delete_admin` | `app.delete("/api/admin/admins/{admin_id}")` | HTTP handler app.delete("/api/admin/admins/{admin_id}") |
| 2828 | async | `admin_logout` | `app.post("/api/admin/auth/logout")` | HTTP handler app.post("/api/admin/auth/logout") |
| 2841 | async | `admin_security` | `app.get("/api/admin/security")` | HTTP handler app.get("/api/admin/security") |
| 2849 | class | `ProductionGateIn` | ` | Операция «ProductionGateIn». |
| 2853 | async | `production_payment_gate` | `app.post("/api/admin/payments/production-gate")` | HTTP handler app.post("/api/admin/payments/production-gate") |
| 2883 | class | `StagingE2EConfigIn` | ` | Операция «StagingE2EConfigIn». |
| 2905 | async | `_staging_config` | ` | Операция «staging config». |
| 2913 | async | `staging_e2e_config` | `app.get("/api/admin/staging-e2e/config")` | HTTP handler app.get("/api/admin/staging-e2e/config") |
| 2924 | async | `update_staging_e2e_config` | `app.put("/api/admin/staging-e2e/config")` | HTTP handler app.put("/api/admin/staging-e2e/config") |
| 2947 | async | `_run_staging_e2e` | ` | Операция «run staging e2e». |
| 2971 | async | `internal_staging_payment` | `app.post("/api/internal/staging-e2e/payment")` | HTTP handler app.post("/api/internal/staging-e2e/payment") |
| 2987 | async | `run_staging_e2e` | `app.post("/api/admin/staging-e2e/run")` | HTTP handler app.post("/api/admin/staging-e2e/run") |
| 3003 | async | `staging_e2e_status` | `app.get("/api/admin/staging-e2e/status")` | HTTP handler app.get("/api/admin/staging-e2e/status") |
| 3012 | async | `setting_value` | ` | Операция «setting value». |
| 3015 | async | `set_setting` | ` | Операция «set setting». |
| 3020 | def | `_backup_path` | ` | Операция «backup path». |
| 3029 | async | `enforce_backup_retention` | ` | Операция «enforce backup retention». |
| 3037 | def | `_database_cli_config` | `` | Return host/user/database/password for PostgreSQL CLI tools from DATABASE_URL. |
| 3053 | async | `create_project_backup` | ` | Операция «create project backup». |
| 3117 | async | `list_backups` | `app.get("/api/admin/backups")` | HTTP handler app.get("/api/admin/backups") |
| 3121 | class | `BackupConfigIn` | ` | Операция «BackupConfigIn». |
| 3132 | async | `backup_config` | `app.get("/api/admin/backups/config")` | HTTP handler app.get("/api/admin/backups/config") |
| 3136 | async | `update_backup_config` | `app.put("/api/admin/backups/config")` | HTTP handler app.put("/api/admin/backups/config") |
| 3146 | async | `run_backup` | `app.post("/api/admin/backups/run")` | HTTP handler app.post("/api/admin/backups/run") |
| 3149 | async | `download_backup` | `app.get("/api/admin/backups/{backup_id}/download")` | HTTP handler app.get("/api/admin/backups/{backup_id}/download") |
| 3157 | async | `delete_backup` | `app.delete("/api/admin/backups/{backup_id}")` | HTTP handler app.delete("/api/admin/backups/{backup_id}") |
| 3162 | async | `backup_scheduler` | ` | Операция «backup scheduler». |
| 3177 | async | `verify_backup` | `app.post("/api/admin/backups/{backup_id}/verify")` | HTTP handler app.post("/api/admin/backups/{backup_id}/verify") |
| 3194 | def | `_validate_tar_safety` | ` | Операция «validate tar safety». |
| 3208 | def | `_safe_extract_members` | ` | Операция «safe extract members». |
| 3217 | async | `validate_backup_archive` | `app.post("/api/admin/backups/{backup_id}/validate")` | HTTP handler app.post("/api/admin/backups/{backup_id}/validate") |
| 3246 | async | `restore_backup` | `app.post("/api/admin/backups/{backup_id}/restore")` | HTTP handler app.post("/api/admin/backups/{backup_id}/restore") |
| 3334 | class | `_PinnedPublicDNSBackend` | `` | httpcore backend that resolves hostnames immediately before each new TCP connection. |
| 3342 | def | `_PinnedPublicDNSBackend.__init__` | ` | Операция «init». |
| 3346 | async | `_PinnedPublicDNSBackend.connect_tcp` | ` | Операция «connect tcp». |
| 3373 | def | `_pinned_public_http_client` | ` | Операция «pinned public http client». |
| 3382 | def | `_resolve_public_host` | ` | Операция «resolve public host». |
| 3405 | def | `validate_public_url` | ` | Операция «validate public url». |
| 3424 | class | `SettingIn` | ` | Операция «SettingIn». |
| 3425 | class | `MenuIn` | ` | Операция «MenuIn». |
| 3431 | class | `FieldIn` | ` | Операция «FieldIn». |
| 3435 | def | `_branding_payload` | ` | Операция «branding payload». |
| 3440 | async | `public_branding` | `app.get("/api/public/branding")` | HTTP handler app.get("/api/public/branding") |
| 3451 | async | `admin_content` | `app.get("/api/admin/content")` | HTTP handler app.get("/api/admin/content") |
| 3465 | async | `admin_setting` | `app.put("/api/admin/settings/{key}")` | HTTP handler app.put("/api/admin/settings/{key}") |
| 3481 | async | `_store_branding_image` | ` | Операция «store branding image». |
| 3505 | async | `_replace_branding_file` | ` | Операция «replace branding file». |
| 3515 | async | `admin_branding_logo` | `app.post("/api/admin/branding/logo")` | HTTP handler app.post("/api/admin/branding/logo") |
| 3521 | async | `admin_branding_favicon` | `app.post("/api/admin/branding/favicon")` | HTTP handler app.post("/api/admin/branding/favicon") |
| 3527 | async | `admin_branding_delete` | `app.delete("/api/admin/branding/{kind}")` | HTTP handler app.delete("/api/admin/branding/{kind}") |
| 3539 | async | `admin_bot_start_image` | `app.post("/api/admin/bot/start-image")` | HTTP handler app.post("/api/admin/bot/start-image") |
| 3561 | async | `admin_bot_start_image_delete` | `app.delete("/api/admin/bot/start-image")` | HTTP handler app.delete("/api/admin/bot/start-image") |
| 3571 | class | `MiniAppConfigIn` | ` | Операция «MiniAppConfigIn». |
| 3579 | async | `admin_miniapp_config` | `app.put("/api/admin/miniapp/config")` | HTTP handler app.put("/api/admin/miniapp/config") |
| 3603 | async | `admin_miniapp_image` | `app.post("/api/admin/miniapp/image")` | HTTP handler app.post("/api/admin/miniapp/image") |
| 3621 | async | `admin_miniapp_image_delete` | `app.delete("/api/admin/miniapp/image")` | HTTP handler app.delete("/api/admin/miniapp/image") |
| 3630 | async | `admin_miniapp_background` | `app.post("/api/admin/miniapp/background")` | HTTP handler app.post("/api/admin/miniapp/background") |
| 3652 | async | `admin_miniapp_background_delete` | `app.delete("/api/admin/miniapp/background")` | HTTP handler app.delete("/api/admin/miniapp/background") |
| 3663 | async | `admin_menu` | `app.post("/api/admin/menu",response_model=dict)` | HTTP handler app.post("/api/admin/menu",response_model=dict) |
| 3676 | async | `admin_menu_update` | `app.put("/api/admin/menu/{item_id}")` | HTTP handler app.put("/api/admin/menu/{item_id}") |
| 3690 | async | `admin_menu_delete` | `app.delete("/api/admin/menu/{item_id}")` | HTTP handler app.delete("/api/admin/menu/{item_id}") |
| 3699 | async | `admin_field` | `app.post("/api/admin/fields")` | HTTP handler app.post("/api/admin/fields") |
| 3703 | async | `admin_field_update` | `app.put("/api/admin/fields/{field_id}")` | HTTP handler app.put("/api/admin/fields/{field_id}") |
| 3710 | async | `admin_field_delete` | `app.delete("/api/admin/fields/{field_id}")` | HTTP handler app.delete("/api/admin/fields/{field_id}") |
| 3715 | async | `_read_upload_limited` | ` | Операция «read upload limited». |
| 3729 | def | `_valid_image_signature` | ` | Операция «valid image signature». |
| 3737 | async | `admin_image` | `app.post("/api/admin/images")` | HTTP handler app.post("/api/admin/images") |
| 3748 | async | `admin_image_delete` | `app.delete("/api/admin/images/{image_id}")` | HTTP handler app.delete("/api/admin/images/{image_id}") |
| 3758 | class | `PromotionIn` | ` | Операция «PromotionIn». |
| 3760 | class | `PromoCodeIn` | ` | Операция «PromoCodeIn». |
| 3762 | class | `AdIn` | ` | Операция «AdIn». |
| 3764 | class | `BroadcastIn` | ` | Операция «BroadcastIn». |
| 3768 | async | `admin_marketing` | `app.get("/api/admin/marketing")` | HTTP handler app.get("/api/admin/marketing") |
| 3773 | async | `create_promotion` | `app.post("/api/admin/promotions")` | HTTP handler app.post("/api/admin/promotions") |
| 3779 | async | `update_promotion` | `app.put("/api/admin/promotions/{item_id}")` | HTTP handler app.put("/api/admin/promotions/{item_id}") |
| 3785 | async | `delete_promotion` | `app.delete("/api/admin/promotions/{item_id}")` | HTTP handler app.delete("/api/admin/promotions/{item_id}") |
| 3791 | async | `create_promo_code` | `app.post("/api/admin/promo-codes")` | HTTP handler app.post("/api/admin/promo-codes") |
| 3799 | async | `update_promo_code` | `app.put("/api/admin/promo-codes/{item_id}")` | HTTP handler app.put("/api/admin/promo-codes/{item_id}") |
| 3806 | async | `delete_promo_code` | `app.delete("/api/admin/promo-codes/{item_id}")` | HTTP handler app.delete("/api/admin/promo-codes/{item_id}") |
| 3812 | async | `create_ad` | `app.post("/api/admin/advertisements")` | HTTP handler app.post("/api/admin/advertisements") |
| 3817 | async | `update_ad` | `app.put("/api/admin/advertisements/{item_id}")` | HTTP handler app.put("/api/admin/advertisements/{item_id}") |
| 3824 | async | `delete_ad` | `app.delete("/api/admin/advertisements/{item_id}")` | HTTP handler app.delete("/api/admin/advertisements/{item_id}") |
| 3830 | async | `create_broadcast` | `app.post("/api/admin/broadcasts")` | HTTP handler app.post("/api/admin/broadcasts") |
| 3836 | async | `monitor_checks_scheduler` | ` | Операция «monitor checks scheduler». |
| 3860 | async | `enterprise_monitoring` | `app.get("/api/admin/enterprise/monitoring")` | HTTP handler app.get("/api/admin/enterprise/monitoring") |
| 3865 | async | `enterprise_monitoring_create` | `app.post("/api/admin/enterprise/monitoring")` | HTTP handler app.post("/api/admin/enterprise/monitoring") |
| 3870 | async | `enterprise_monitoring_delete` | `app.delete("/api/admin/enterprise/monitoring/{check_id}")` | HTTP handler app.delete("/api/admin/enterprise/monitoring/{check_id}") |
| 3876 | async | `enterprise_campaigns` | `app.get("/api/admin/enterprise/campaigns")` | HTTP handler app.get("/api/admin/enterprise/campaigns") |
| 3880 | async | `enterprise_campaign_create` | `app.post("/api/admin/enterprise/campaigns")` | HTTP handler app.post("/api/admin/enterprise/campaigns") |
| 3884 | async | `enterprise_campaign_update` | `app.put("/api/admin/enterprise/campaigns/{campaign_id}")` | HTTP handler app.put("/api/admin/enterprise/campaigns/{campaign_id}") |
| 3891 | async | `enterprise_rules` | `app.get("/api/admin/enterprise/rules")` | HTTP handler app.get("/api/admin/enterprise/rules") |
| 3895 | async | `enterprise_rule_create` | `app.post("/api/admin/enterprise/rules")` | HTTP handler app.post("/api/admin/enterprise/rules") |
| 3899 | async | `enterprise_rule_update` | `app.put("/api/admin/enterprise/rules/{rule_id}")` | HTTP handler app.put("/api/admin/enterprise/rules/{rule_id}") |
| 3906 | async | `enterprise_summary` | `app.get("/api/admin/enterprise/summary")` | HTTP handler app.get("/api/admin/enterprise/summary") |
| 3923 | async | `_ensure_v41_defaults` | ` | Операция «ensure v41 defaults». |
| 3933 | async | `v41_features` | `app.get("/api/admin/v41/features")` | HTTP handler app.get("/api/admin/v41/features") |
| 3938 | class | `FeatureFlagIn` | ` | Операция «FeatureFlagIn». |
| 3942 | async | `v41_feature_update` | `app.put("/api/admin/v41/features/{key}")` | HTTP handler app.put("/api/admin/v41/features/{key}") |
| 3951 | async | `v41_analytics` | `app.get("/api/admin/v41/analytics")` | HTTP handler app.get("/api/admin/v41/analytics") |
| 3964 | async | `v41_crm_users` | `app.get("/api/admin/v41/crm/users")` | HTTP handler app.get("/api/admin/v41/crm/users") |
| 3974 | async | `v41_providers` | `app.get("/api/admin/v41/providers")` | HTTP handler app.get("/api/admin/v41/providers") |
| 3979 | class | `ProviderHealthIn` | ` | Операция «ProviderHealthIn». |
| 3984 | async | `v41_provider_update` | `app.put("/api/admin/v41/providers/{provider}")` | HTTP handler app.put("/api/admin/v41/providers/{provider}") |
| 3992 | async | `v41_diagnostics` | `app.get("/api/admin/v41/diagnostics")` | HTTP handler app.get("/api/admin/v41/diagnostics") |
| 4007 | class | `IncidentCreateIn` | ` | Операция «IncidentCreateIn». |
| 4014 | async | `v41_incidents` | `app.get("/api/admin/v41/incidents")` | HTTP handler app.get("/api/admin/v41/incidents") |
| 4019 | async | `v41_incident_create` | `app.post("/api/admin/v41/incidents")` | HTTP handler app.post("/api/admin/v41/incidents") |
| 4023 | async | `v41_incident_resolve` | `app.post("/api/admin/v41/incidents/{incident_id}/resolve")` | HTTP handler app.post("/api/admin/v41/incidents/{incident_id}/resolve") |
| 4029 | async | `v41_backup_verification_list` | `app.get("/api/admin/v41/backups/verification")` | HTTP handler app.get("/api/admin/v41/backups/verification") |
| 4034 | async | `v41_backup_test_restore` | `app.post("/api/admin/v41/backups/{backup_id}/test-restore")` | HTTP handler app.post("/api/admin/v41/backups/{backup_id}/test-restore") |
| 4092 | async | `v41_referrals` | `app.get("/api/admin/v41/referrals")` | HTTP handler app.get("/api/admin/v41/referrals") |
| 4097 | async | `v41_promotions` | `app.get("/api/admin/v41/promotions")` | HTTP handler app.get("/api/admin/v41/promotions") |
| 4105 | async | `v41_passkeys` | `app.get("/api/admin/v41/passkeys")` | HTTP handler app.get("/api/admin/v41/passkeys") |
| 4110 | async | `v41_passkey_delete` | `app.delete("/api/admin/v41/passkeys/{credential_id}")` | HTTP handler app.delete("/api/admin/v41/passkeys/{credential_id}") |

### Фоновый worker

Файл: `backend/worker.py`.

| Строка | Вид | Имя | Контракт | Назначение |
| --- | --- | --- | --- | --- |
| 12 | async | `job_worker` | ` | Операция «job worker». |
| 129 | async | `health_alert_worker` | ` | Операция «health alert worker». |
| 145 | async | `worker_heartbeat` | ` | Операция «worker heartbeat». |
| 162 | async | `main_worker` | ` | Операция «main worker». |
