# Модули проекта / Project modules

Версия **3.1.6**. Админка не отвечает 502: nginx пишет в `/tmp/nginx` — раздел 9.20 `INSTRUCTION.md`. Админка, Mini App и кабинет пишут кэш nginx во временные каталоги — раздел 9.19 `INSTRUCTION.md`. Первый запуск сериализует миграции — раздел 9.18 `INSTRUCTION.md`. Исправления **3.1.2**, **3.1.1**, **3.1.0** и **3.0.1** остаются в силе. Установка через `curl | bash` читает вопросы с терминала — раздел 9.17 `INSTRUCTION.md`. Предыдущее описание скачивания относится к **2.13.0**, аудит 3.0.0-realise остаётся в силе. Этот документ объясняет, зачем существует каждый модуль. Пошаговая установка — `INSTALL_STEPS.md`. Аудит ответов панели — раздел 9.16 `INSTRUCTION.md`. Staging E2E и production gate — раздел 9.15 `INSTRUCTION.md`. Скачивание приложений описано в разделе 9.11 `INSTRUCTION.md`. Массовая рассылка Telegram описана в разделе 9.10 `INSTRUCTION.md`. Построчный разбор функций API остаётся в `FUNCTIONS.md`. Установка и проверка без касс — в `INSTRUCTION.md`, раздел 9.4. Платформа 2.6.0 — в разделе 9.5. Приложения Android и iOS — в разделе 9.6 и в `MOBILE.md`. Тексты и логотип приложений — в разделе 9.7. Установка APK 2.9.0 — в разделе 9.8. Подпись клиента, release APK и обновление с GitHub — в разделе 9.9. Предыдущее описание конструктора относится к **2.5.0**. Каталог приложений описан для **2.8.0**.

Version **3.1.6**. The admin UI does not answer 502: nginx writes under `/tmp/nginx`; that is section 9.20 of `INSTRUCTION.md`. The admin UI, Mini App, and cabinet write the nginx cache on temporary mounts; that is section 9.19 of `INSTRUCTION.md`. The first boot serializes migrations; that is section 9.18 of `INSTRUCTION.md`. The **3.1.2**, **3.1.1**, **3.1.0**, and **3.0.1** fixes still apply. A `curl | bash` install reads questions from the terminal; that is section 9.17 of `INSTRUCTION.md`. The previous download description belongs to **2.13.0**, and the 3.0.0-realise audit still applies. This document explains why each module exists. The step-by-step install is `INSTALL_STEPS.md`. The panel-response audit is section 9.16 of `INSTRUCTION.md`. Staging E2E and the production gate are section 9.15 of `INSTRUCTION.md`. App downloads are described in section 9.11 of `INSTRUCTION.md`. The Telegram mass broadcast is described in section 9.10 of `INSTRUCTION.md`. The function-by-function API map stays in `FUNCTIONS.md`. Install steps and the gateway-free test are in `INSTRUCTION.md`, section 9.4. The 2.6.0 platform is in section 9.5. The Android and iOS apps are in section 9.6 and in `MOBILE.md`. App texts and the logo are in section 9.7. The 2.9.0 APK install is in section 9.8. Client proof, the release APK and the GitHub update are in section 9.9. The constructor description belongs to **2.5.0**. The app catalog belongs to **2.8.0**.

---

## Русский

### Как устроен запрос

Покупатель открывает Mini App, личный кабинет или бота. Администратор открывает панель. Caddy принимает HTTPS и отдаёт статику `admin`, `miniapp` или `cabinet`, а `/api` отправляет в FastAPI. API читает и пишет PostgreSQL, ставит блокировки и лимиты в Redis, ходит в Remnawave за пользователями и узлами и в платёжного провайдера за созданием и сверкой платежа. Фоновый `worker` дожимает очередь задач. Планировщики внутри API-процесса повторяют выдачу, возвраты, автопродление, сверку и уведомления об окончании подписки.

### `backend/app/mobile_catalog.py`

Хранит четыре карточки приложений, логотип кабинета и загруженные APK/IPA. Публичный маршрут отдаёт только включённые карточки покупателя, безопасный путь `/media/` и ссылку скачивания покупателя. Пакет администратора отдаёт только `GET /api/admin/apps/{id}/download`. Запись, логотип и файл требуют `manage_content`.

### `backend/app/mobile_auth.py`

Решает, можно ли отдать JWT в теле ответа. Список клиентов: `android-user`, `android-admin`, `ios-user`, `ios-admin`. Для них `session_body` добавляет `access_token`. Для браузера тело остаётся без токена, а cookie ставит вызывающий обработчик. С версии 2.10.0 `require_mobile_proof` проверяет HMAC, если заголовок клиента известен и `MOBILE_REQUIRE_PROOF` включён.

### `backend/app/github_update.py`

Читает последний релиз `booarkz-cpu/remnawave-vpn-shop` у `api.github.com` без редиректов и без доверия к переменным прокси. Отдаёт сравнение версий и allowlist ссылок на файлы релиза. Архив не скачивает и на диск не пишет. Применение остаётся у `scripts/update-from-github.sh` на хосте.

### `backend/app/main.py`

Главный HTTP-процесс магазина. Здесь собраны:

- версия приложения и маршруты здоровья `/health`, `/health/live`, `/health/ready`;
- сессии покупателя и администратора, CSRF, rate limit, ограничение размера тела;
- каталог тарифов, промокоды, пробный период, устройства;
- создание платежа, вебхуки YooKassa / Platega / RollyPay, выдача `fulfill`, возвраты;
- кошелёк, подарки, рефералы, поддержка, уведомления;
- админские разделы: пользователи, платежи, бэкапы, аудит, роли, staging, мониторинг процессов;
- подключение роутеров кабинета и конструктора.

С версии 2.5.0 оплата и списание кошелька, если в теле есть `constructor_id`, берут цену и лимиты из `quote_constructor` и пишут их в снимок платежа. Якорный тариф конструктора нельзя купить, подарить или взять на пробу в обход пунктов.

### `backend/app/cabinet_api.py`

Отдельный контур личного кабинета, чтобы не смешивать его с Telegram-only входом.

- регистрация и вход по email и паролю;
- старт и callback VK ID;
- публичное меню кабинета и админский CRUD вкладок;
- тексты инструкций для Android, iOS, TV, Windows, macOS и Linux;
- завершение sandbox-платежа `POST /api/payments/sandbox/complete`.

Вид вкладки `servers` разрешён с 2.5.0: кабинет показывает статус узлов, а не произвольный HTML.

### `backend/app/tariff_api.py`

Конструктор тарифа и безопасный статус узлов.

- хранит конструктор и пункты видов `devices`, `traffic_gb`, `days`;
- проверяет диапазоны и требует по одному включённому пункту каждого вида, если конструктор включён;
- синхронизирует скрытый якорный `Plan`, чтобы у платежа оставался `plan_id`;
- `quote_constructor` считает сумму и возвращает дни, трафик и устройства выбранной комбинации;
- `public_node` оставляет только имя, страну, статус и число пользователей онлайн;
- маршруты: публичный список конструкторов, публичный статус серверов, статус для вошедшего пользователя, мониторинг для администратора, CRUD конструктора.

Отключение конструктора не удаляет строки: новые покупки закрываются, история платежей остаётся.

### `backend/app/abuse.py`

Чистый скоринг без базы данных. Считает префикс источника, расстояние между точками и рекомендацию observe / warn / review / throttle / block. Его вызывают наблюдения агента.

### `backend/app/platform_api.py`

Операторская платформа: политика антиабьюза, переключатели модулей, агенты, чёрный список, разбор нарушений, ключи API, подписанные webhook, SMTP и DKIM, heartbeat и приём наблюдений, `GET /api/v3/status`, строки Prometheus. Секреты создания не попадают в сводку.

### `scripts/node-agent.py`

Процесс на узле. Шлёт метрики и файл наблюдений, забирает очередь `throttle` и `clear`. Ограничение трафика включается переменной `AGENT_APPLY_TC=1`.

### `backend/app/payments.py`

Адаптеры касс. `YooKassaProvider`, `PlategaProvider` и `RollyPayProvider` создают платёж, читают его статус и делают возврат. `SandboxProvider` существует только для проверки без живых шлюзов: идентификатор начинается с `sandbox-`, статус сразу `succeeded`, URL ведёт в кабинет с `?sandbox_payment=`. Проверка подписи и allowlist живых провайдеров живёт рядом с этими классами и вызывается из `main.py` до выдачи.

### `backend/app/remnawave.py`

Клиент панели Remnawave: пользователи, срок, лимиты трафика и устройств, список узлов, ключ подключения. Здесь же предохранитель на повторные ошибки, чтобы сбой панели не зацикливал выдачу. Модуль не решает, какие поля можно показать покупателю: это делает `tariff_api.public_node`.

### `backend/app/security.py`

Пароли scrypt, шифрование секретов от `APP_SECRET`, выпуск и проверка JWT, текущий администратор, роли и права, TOTP и коды восстановления. Конструктор требует право `manage_plans`. Чтение мониторинга требует `read`.

### `backend/app/config.py`

Все настройки из окружения: база, Redis, домены, бот, Remnawave, кассы, `PAYMENTS_SANDBOX`, `CABINET_URL`, `CABINET_DOMAIN`, VK, Яндекс, лимит пробного периода, CORS, cookie. Пустые строки касс не должны ронять процесс: sandbox как раз позволяет поднять магазин до подключения шлюза.

### `backend/app/models.py`

Таблицы SQLAlchemy: пользователи, тарифы, платежи со снимками, подписки, сессии, промокоды, подарки, кошелёк, журнал, аудит, меню кабинета, конструктор и его пункты, кампании, задачи, бэкапы. Платёж хранит снимок, чтобы правка тарифа после оплаты не меняла уже купленное.

### `backend/app/db.py`

Движок async SQLAlchemy и зависимость `get_db` для запросов. Миграции применяет Alembic, не этот файл.

### `backend/app/bot.py`

Telegram-бот на aiogram. Приветствие, цены, кнопка магазина, команды промокода и подарка, рассылки и `/ops` для `ADMIN_TELEGRAM_ID`. Тексты есть на русском и английском. Бот не принимает деньги сам: он открывает Mini App. С версии 2.12.0 `broadcast_worker` забирает строки `queued`, сохраняет прогресс после каждого получателя, помечает оборванную отправку как `failed` и продолжает повтор с `sent_count + failed_count`. API только ставит строку в очередь.

### `backend/app/provisioner.py`

Редкое действие администратора: по SSH выложить compose узла. Соединение требует отпечаток host key. Это не мониторинг и не пользовательский статус. Секреты SSH не сохраняются как постоянные учётные данные панели.

### `backend/app/totp.py`

Генерация и проверка TOTP и otpauth URI для приложения-аутентификатора администратора.

### `backend/worker.py`

Отдельный процесс очереди. Забирает задачи `Job` (в том числе пробный период), ведёт heartbeat `WorkerState`, не даёт двум воркерам взять одну строку (`skip_locked`) и возвращает в очередь зависшие задачи. Выдача после оплаты тоже может быть дожата планировщиком API, если вызов Remnawave оборвался.

### `backend/alembic/versions/`

История схемы. Голова 2.5.0 — `0037_v2_5_0_tariff_constructor`: таблицы конструктора и вкладка кабинета «Серверы». Предыдущая голова 2.4.0 — `0036_v2_4_0_cabinet`.

### `admin/`

Панель администратора на React. Вкладки покрывают бренд, обзор, тарифы, конструктор, мониторинг Remnawave, платформу, платежи, пользователей, контент бота и Mini App, CMS кабинета, маркетинг, роли, бэкапы, безопасность, восстановление, аудит и операции. Семь тем задаются CSS-переменными. Русские подписи переводятся словарём `admin/src/i18n.tsx`, когда выбран английский.

### `miniapp/`

Магазин внутри Telegram. Показывает подписку, обычные тарифы, конструктор, статус серверов, кошелёк, подарки, рефералы и поддержку. Оплата использует тот же API, что и кабинет.

### `cabinet/`

Отдельное SPA личного кабинета. Вход: email, Telegram, VK, Яндекс. Вкладки приходят из CMS; если вкладки «Серверы» нет, клиент добавляет её сам. Покупка конструктора и обычного тарифа, пробный период, ссылка подписки и инструкции по устройствам живут здесь. Возврат `?sandbox_payment=` завершает тестовый платёж.

### `mobile/`

Четыре приложения версии 2.7.0. `android-user` и `ios-user` — покупатель. `android-admin` и `ios-admin` — администратор. Общие правила адреса и узла лежат в `mobile/client_rules.py`. Kotlin и Swift повторяют те же правила. Строки — `mobile/l10n/user.json` и `mobile/l10n/admin.json`. `mobile/LICENSE` указывает на корневую проприетарную лицензию. Docker Compose эти приложения не запускает.

### `deploy/` и `docker-compose.yml`

Compose поднимает `db`, `redis`, `backend`, `worker`, `bot`, `admin`, `miniapp`, `cabinet` и `caddy`. Caddy выпускает сертификаты и разделяет домены API, админки, Mini App и кабинета. `install.sh` вызывает `deploy/install-vps.sh`: Docker, `.env`, миграции, UFW и Fail2Ban.

### `scripts/`

| Скрипт | Зачем |
| --- | --- |
| `sandbox-e2e.sh` | Полный прогон оплаты без живых касс и проверка, что статус узлов не содержит секретов |
| `build-release.sh` | Проверки и ZIP релиза |
| `integration-test.sh` | Проверка compose на хосте с Docker |
| `preflight.sh` | Проверка окружения перед запуском |
| `doctor.sh` | Быстрая диагностика работающего стека |
| `security-scan.sh` | Поиск опасных настроек |
| `update.sh` / `rollback.sh` | Обновление и откат |

### `tests/`

Контрактные тесты читают исходники и проверяют, что версия, миграция, кабинет, sandbox, конструктор, мониторинг и двуязычные документы на месте. Они не подменяют прогон `sandbox-e2e.sh` против живого API.

---

## English

### Request path

A buyer opens the Mini App, the cabinet or the bot. An administrator opens the panel. Caddy terminates HTTPS, serves the `admin`, `miniapp` or `cabinet` files, and forwards `/api` to FastAPI. The API uses PostgreSQL for state, Redis for locks and rate limits, Remnawave for users and nodes, and a payment provider to create and re-read payments. `worker` drains the job queue. Schedulers inside the API process retry fulfillment, refunds, auto-renew, reconciliation and expiry notices.

### `backend/app/mobile_catalog.py`

Stores the four app cards, the cabinet logo and uploaded APK/IPA files. The public route returns only enabled buyer cards, a safe `/media/` path and the buyer download link. The administrator package is served only by `GET /api/admin/apps/{id}/download`. Saving the catalog, the logo and the file requires `manage_content`.

### `backend/app/mobile_auth.py`

Decides whether the JWT may appear in the response body. The client list is `android-user`, `android-admin`, `ios-user` and `ios-admin`. For those names `session_body` adds `access_token`. A browser response stays without the token, and the caller sets the cookie. From 2.10.0, `require_mobile_proof` checks the HMAC when the client header is known and `MOBILE_REQUIRE_PROOF` is on.

### `backend/app/github_update.py`

Reads the latest `booarkz-cpu/remnawave-vpn-shop` release from `api.github.com` without following redirects and without trusting proxy environment variables. It returns the version comparison and an allowlist of release file URLs. It does not download or extract the archive. Applying the update stays with `scripts/update-from-github.sh` on the host.

### `backend/app/main.py`

The shop HTTP process: version and health routes, buyer and admin sessions, CSRF, rate limits, body size, the plan catalog, promos, trials, devices, payment creation, YooKassa / Platega / RollyPay webhooks, `fulfill`, refunds, wallet, gifts, referrals, support, notifications, and the admin operations surface. It mounts the cabinet and tariff routers.

From 2.5.0, checkout and wallet spend call `quote_constructor` when `constructor_id` is present and store that quote on the payment. The constructor anchor plan cannot be bought, gifted or trialed by its raw plan id.

### `backend/app/cabinet_api.py`

The user cabinet boundary: email registration and login, VK ID start and callback, the public menu, admin menu CRUD, device-guide text, and `POST /api/payments/sandbox/complete`. The menu kind `servers` is allowed so the cabinet can show node status.

### `backend/app/abuse.py`

Database-free scoring. It builds the source prefix, the distance between points and the recommendation observe / warn / review / throttle / block. Agent observations call it.

### `backend/app/platform_api.py`

The operator platform: abuse policy, module toggles, agents, the HWID blacklist, violation review, API keys, signed webhooks, SMTP and DKIM, heartbeat, observation ingest, `GET /api/v3/status` and Prometheus lines. Create-time secrets stay out of the summary.

### `scripts/node-agent.py`

The process on a node. It posts metrics and an observations file and collects `throttle` and `clear`. Traffic control runs only when `AGENT_APPLY_TC=1`.

### `backend/app/tariff_api.py`

Tariff constructor and safe node status. It stores constructors and `devices`, `traffic_gb` and `days` options, validates ranges, keeps a hidden anchor `Plan`, prices a selection in `quote_constructor`, and strips node payloads down to name, country, status and online users. Routes cover the public constructor list, public servers, the signed-in server view, admin monitoring, and constructor CRUD. Disabling a constructor closes new sales and keeps payment history.

### `backend/app/payments.py`

Gateway adapters. YooKassa, Platega and RollyPay create, read and refund payments. `SandboxProvider` is the gateway-free path: ids start with `sandbox-`, status is `succeeded`, and the URL returns to the cabinet with `?sandbox_payment=`.

### `backend/app/remnawave.py`

Remnawave panel client for users, expiry, traffic and device limits, the node list and the connection key, plus a circuit breaker. It does not decide which fields a buyer may see; `public_node` does.

### `backend/app/security.py`

scrypt passwords, secret encryption, JWT, the current admin, RBAC, TOTP and recovery codes. Constructor writes need `manage_plans`. Monitoring reads need `read`.

### `backend/app/config.py`

Environment settings: database, Redis, domains, bot, Remnawave, gateways, `PAYMENTS_SANDBOX`, cabinet URL and domain, VK, Yandex, trial cap, CORS and cookies. Empty gateway secrets must not prevent a sandbox boot.

### `backend/app/models.py`

SQLAlchemy tables for users, plans, snapshotted payments, subscriptions, sessions, promos, gifts, the wallet, the ledger, audit, the cabinet menu, the constructor and its options, campaigns, jobs and backups.

### `backend/app/db.py`

The async SQLAlchemy engine and `get_db`. Alembic owns schema changes.

### `backend/app/bot.py`

The aiogram Telegram bot: welcome, prices, the shop button, promo and gift commands, broadcasts, and `/ops` for `ADMIN_TELEGRAM_ID`. Copy exists in Russian and English. The bot does not charge cards; it opens the Mini App. From 2.12.0, `broadcast_worker` claims `queued` rows, saves progress after each recipient, marks a crashed send as `failed`, and continues a retry from `sent_count + failed_count`. The API only queues the row.

### `backend/app/provisioner.py`

An administrator-only SSH compose deploy for a node. The host key fingerprint is required. This is not the user-facing status page.

### `backend/app/totp.py`

TOTP generation, verification and the otpauth URI for the admin authenticator app.

### `backend/worker.py`

The queue process. It claims `Job` rows, including trials, writes `WorkerState`, uses `skip_locked`, and requeues abandoned jobs.

### `backend/alembic/versions/`

Schema history. The 2.6.0 head is `0038_v2_6_0_platform`. The 2.5.0 head was `0037_v2_5_0_tariff_constructor`. The 2.4.0 head was `0036_v2_4_0_cabinet`.

### `admin/`, `miniapp/`, `cabinet/`

`admin` is the operator console, including the plan builder, Remnawave monitoring, the platform desk and seven themes. `miniapp` is the Telegram shop with plans, the constructor and server status. `cabinet` is the standalone account with email, Telegram, VK and Yandex sign-in, CMS-driven tabs, constructor checkout, trial, the subscription link, device guides and a web app manifest. Russian source strings are translated by each app's `i18n.tsx` when English is selected, including `aria-label` and the “Онлайн N из M” pattern.

### `mobile/`

Four native clients for version 2.7.0. `android-user` and `ios-user` are the buyer apps. `android-admin` and `ios-admin` are the administrator apps. Shared URL and node rules live in `mobile/client_rules.py` so tests can lock them. The Kotlin and Swift sources duplicate those rules. String catalogs are `mobile/l10n/user.json` and `mobile/l10n/admin.json`, copied into each app. `mobile/LICENSE` points at the root proprietary license. The apps are not started by Docker Compose.

### `deploy/`, Compose and `scripts/`

Compose runs PostgreSQL, Redis, the API, the worker, the bot, three frontends and Caddy. `install.sh` delegates to `deploy/install-vps.sh`. `scripts/sandbox-e2e.sh` is the pre-release payment test without live gateways. The other scripts build a release, check Compose, preflight the host, diagnose a running stack, scan settings, update and roll back.

### `tests/`

Source-contract tests keep the version, migration, cabinet, sandbox, constructor, monitoring and bilingual docs wired. They do not replace `sandbox-e2e.sh` against a running API.
