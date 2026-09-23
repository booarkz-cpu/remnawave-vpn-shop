# Пошаговая установка — Remnawave VPN Shop 3.1.6

Этот файл — отдельная установка с нуля. Каждый вопрос ниже совпадает с вопросом `deploy/install-vps.sh`. Панель staging E2E и кнопка «Разрешить реальные платежи» описаны в разделе 9.15 `INSTRUCTION.md`.

## Русский

### 1. Что будет установлено

На Debian или Ubuntu скрипт ставит Docker Engine и Docker Compose, копирует проект в `/opt/vpn-shop`, пишет `.env` с правами `0600`, собирает образы, поднимает PostgreSQL 16, Redis 7, API, worker, бота, админку, Mini App, личный кабинет и Caddy. Миграции Alembic доходят до `0038_v2_6_0_platform`. Версия установщика — **3.1.6**. Админка, Mini App и кабинет отвечают на HTTP, nginx пишет в `/tmp/nginx`. Вопросы те же, что в **3.1.5**, **3.1.4**, **3.1.3**, **3.1.2** и **3.1.1**. Пробелы по краям ответа снимаются. `Moscow` записывается как `Europe/Moscow`.

Наружу остаются SSH, TCP 80, TCP 443 и UDP 443. PostgreSQL, Redis, API и панели в firewall не публикуются. Их отдаёт Caddy по своим доменам.

### 2. Что подготовить до команды

1. Чистый VPS с Debian или Ubuntu и доступ root по SSH.
2. Домены, чьи DNS-записи типа A (и AAAA, если используете IPv6) уже указывают на IP этого VPS. Сертификат выпустится только после этого.
3. Токен бота от @BotFather и имя бота без `@`.
4. URL панели Remnawave с `https://` и API-токен этой панели.
5. Для боевой кассы — реквизиты YooKassa, Platega или RollyPay. Для первого запуска допустим ответ `none`: магазин поднимется, а живые платежи останутся выключенными до раздела 9.15.
6. Почта администратора и пароль не короче 12 символов. Пустой пароль скрипт заменит на `openssl rand -hex 16` и напечатает его один раз в конце.

Поля staging E2E в эти вопросы не входят. Сюда пишутся реквизиты магазина. Sandbox-ключи кассы вводятся позже в панели и не должны совпадать со значениями из `.env`.

### 3. Имена доменов

Если основной домен `vpn.example.com`, скрипт предложит:

| Вопрос | Значение по умолчанию |
| --- | --- |
| API-домен | `api.vpn.example.com` |
| Домен админки | `admin.vpn.example.com` |
| Домен Mini App | `app.vpn.example.com` |
| Домен личного кабинета | `cabinet.vpn.example.com` |
| Домен вебхуков | `pay.vpn.example.com` |
| Домен бота | `bot.vpn.example.com` |

Создайте DNS-записи для каждого имени, которое оставите. `PANEL_DOMAIN` по умолчанию равен основному домену и нужен, только если Caddy должен ещё и открывать панель Remnawave.

### 4. Запуск

Из каталога уже скачанного релиза, на сервере:

```bash
sudo bash install.sh
```

С GitHub, на чистом сервере:

```bash
curl -fsSL https://raw.githubusercontent.com/booarkz-cpu/remnawave-vpn-shop/main/install.sh | sudo bash
```

`install.sh` проверяет root, ставит `ca-certificates`, `curl`, `git`, `openssl` и Docker, затем передаёт управление `deploy/install-vps.sh`. Запуск через `curl` клонирует ветку `main` в `/opt/vpn-shop-src`. Запуск из каталога проекта использует этот каталог. Если `/opt/vpn-shop` уже содержит `docker-compose.yml` или `.env`, скрипт останавливается и просит обновлять существующую копию, а не ставить вторую.

Канал `curl | bash` занят текстом скрипта, поэтому вопросы читаются с терминала SSH (`/dev/tty`). В **3.1.2** первый вопрос на этом канале завершался строкой `installation failed at line 34`. С **3.1.3** тот же запуск дожидается ответа в терминале. Без терминала задайте `INSTALL_NONINTERACTIVE=1` и переменные окружения.

### 5. Ответы по порядку

Скрипт печатает, что DNS уже должен указывать на этот VDS, затем спрашивает:

1. `Основной домен (например vpn.example.com)` — обязательное поле, латиница, цифры, точки и дефис.
2. `API-домен` — Enter оставляет `api.<основной>`.
3. `Домен админки` — Enter оставляет `admin.<основной>`.
4. `Домен Mini App` — Enter оставляет `app.<основной>`.
5. `Домен личного кабинета` — Enter оставляет `cabinet.<основной>`.
6. `Email администратора` — Enter оставляет `admin@<основной>`.
7. `Пароль администратора (Enter = сгенерировать)` — ввод скрыт. Enter оставляет генерацию на конец скрипта.
8. `Telegram BOT_TOKEN от @BotFather` — обязательное поле, ввод скрыт.
9. `Remnawave Panel URL` — обязательный `https://` URL панели.
10. `Remnawave API token` — обязательное поле, ввод скрыт.
11. `Провайдер (yookassa / platega / rollypay / none)` — по умолчанию `none`.
12. Для `yookassa`: `YooKassa Shop ID` и скрытый `YooKassa Secret Key`.
13. Для `platega`: `Platega Merchant ID` и скрытый `Platega Secret`.
14. Для `rollypay`: скрытые `RollyPay API Key` и `RollyPay Signing Secret`.
15. Дополнительные кассы. Для провайдеров, которые не выбраны на шаге 11, скрипт спрашивает Shop ID / Merchant ID / API Key. Секрет спрашивается, только если идентификатор не пустой. Enter оставляет поле пустым.
16. `Platega refund URL` и `RollyPay refund URL`. Пустые значения допустимы, пока возврат через эту кассу не нужен.
17. `Имя бота без @` — обязательное поле.
18. `Telegram ID администратора (@userinfobot)` — числовой ID. Пустое значение допустимо, тогда команда `/ops` не привязана к человеку.
19. `Язык по умолчанию (ru/en)` — по умолчанию `ru`. Другое значение скрипт отклоняет.
20. `Валюта` — по умолчанию `RUB`.
21. `Часовой пояс` — по умолчанию `Europe/Moscow`.
22. `Email для TLS-сертификата` — по умолчанию почта администратора.
23. `Домен вебхуков` — по умолчанию `pay.<основной>`.
24. `Домен Mini App, если отличается` — по умолчанию домен Mini App из шага 4.
25. `Домен бота` — по умолчанию `bot.<основной>`.
26. `Домен панели Remnawave в Caddy, если нужен` — по умолчанию основной домен.
27. `Цена 1 месяц` — `199`. `Цена 3 месяца` — `499`. `Цена 6 месяцев` — `899`. `Цена 12 месяцев` — `1499`.
28. `Автопродление (true/false)` — по умолчанию `false`.
29. `За сколько дней до конца списывать автопродление` — по умолчанию `3`.
30. `Обязательный канал (@name или -100..., Enter = выкл)`.
31. `Telegram-чат алертов`.
32. `Процент реферального вознаграждения` — по умолчанию `5.0`.
33. `За сколько дней предупреждать об окончании` — по умолчанию `3`.
34. `Yandex OAuth Client ID` и скрытый `Yandex OAuth Client Secret`. Enter пропускает вход через Яндекс.
35. `VK OAuth Client ID` и скрытый `VK OAuth Client Secret`. Enter пропускает вход через VK.
36. `Песочница платежей без шлюзов (true/false)` — по умолчанию `false`. Значение `true` включает `PAYMENTS_SANDBOX` для локальной проверки `scripts/sandbox-e2e.sh`. Этот флаг не открывает production gate.
37. `Максимум дней пробного периода` — по умолчанию `3`.
38. `S3 endpoint`. Enter отключает внешнюю копию. Если endpoint задан, заполните `S3 bucket`, `S3 region` (по умолчанию `auto`), `S3 access key` и скрытый `S3 secret key`.

Дальше скрипт сам создаёт `APP_SECRET` и пароль PostgreSQL, ставит UFW и Fail2Ban для SSH, фиксирует digest базовых образов, собирает lock-файлы фронтенда, собирает контейнеры и ждёт `GET /health` внутри контейнера `backend`.

### 6. Установка без вопросов

Экспортируйте переменные и запустите:

```bash
export INSTALL_NONINTERACTIVE=1
export BASE_DOMAIN=vpn.example.com
export ADMIN_EMAIL=admin@vpn.example.com
export ADMIN_PASSWORD='замените-на-свой-пароль'
export BOT_TOKEN='токен-от-BotFather'
export REMNAWAVE_URL='https://panel.example.com'
export REMNAWAVE_TOKEN='токен-remnawave'
export BOT_USERNAME='имя_бота_без_собаки'
export PAYMENT_PROVIDER=none
sudo --preserve-env bash install.sh
```

Пустая обязательная переменная останавливает скрипт с текстом `Не задано обязательное поле`. Остальные имена берут значения по умолчанию из раздела 5: `API_DOMAIN`, `ADMIN_DOMAIN`, `APP_DOMAIN`, `CABINET_DOMAIN`, `DEFAULT_LANGUAGE`, `DEFAULT_CURRENCY`, `TZ_VALUE`, `CADDY_EMAIL`, `WEBHOOK_DOMAIN`, `PRICE_1`, `PRICE_3`, `PRICE_6`, `PRICE_12`, `AUTO_RENEW_ENABLED`, `AUTO_RENEW_LEAD_DAYS`, `REFERRAL_REWARD_PERCENT`, `NOTIFICATION_EXPIRY_DAYS`, `PAYMENTS_SANDBOX`, `TRIAL_MAX_DAYS`.

### 7. Что проверить сразу после установки

В конце скрипт печатает адреса Admin, Mini App, Cabinet и API, версию `3.1.6` и почту администратора. Сгенерированный пароль печатается одной строкой `Admin password (generated)`. Сохраните его вне сервера и включите 2FA: админка → **Безопасность**.

```bash
curl -fsS "https://api.ВАШ-ДОМЕН/health"
cd /opt/vpn-shop
docker compose ps
./scripts/doctor.sh
```

Ответ `/health` содержит `"ok": true`, `"version": "3.1.6"`, `"database": true` и `"redis": true`. Предыдущий релиз отвечал `"version": "3.1.5"`. Релиз **3.1.4** отвечал `"version": "3.1.4"`. Релиз **3.1.3** отвечал `"version": "3.1.3"`. Релиз **3.1.2** отвечал `"version": "3.1.2"`. Команда проверки — `curl -fsS`, не `url`. `docker compose ps` должен показывать `admin`, `miniapp` и `cabinet` как `Up`, а не `Restarting`. `doctor.sh` рассчитан на каталог `/opt/vpn-shop` и запущенный Docker.

Откройте `https://admin.<домен>`, войдите почтой и паролем администратора. Создайте хотя бы один включённый тариф: его числовой ID понадобится в staging E2E.

Для YooKassa в `.env` уже записан стартовый `YOOKASSA_WEBHOOK_IP_ALLOWLIST`. Сверьте его с актуальным списком сетей провайдера и укажите в кабинете кассы URL `https://pay.<домен>`. Пустой список даёт ответ 403 `Webhook IP not allowed`.

### 8. Staging E2E и production gate

После входа под ролью `admin`:

1. Откройте **Проверка тестового контура**.
2. Заполните публичный HTTPS URL этого магазина, HTTPS URL staging Remnawave, токен staging и ID тестового тарифа.
3. Включите только те кассы, для которых есть sandbox-ключи. Эти ключи вводятся здесь, а не в `.env`.
4. Отметьте **Подтверждаю sandbox-ключи** и нажмите **Сохранить безопасную конфигурацию**.
5. Нажмите **Запустить staging E2E** и откройте строки `[CHECKOUT]` в журнале карточки.
6. Кнопка **Разрешить реальные платежи** на вкладке **Безопасность** принимает включение, когда журнал содержит `FULL_E2E_PASS` и `finished_at` моложе 24 часов.

Полный порядок, ответы 409 и смысл статуса `awaiting_checkout` — раздел 9.15 `INSTRUCTION.md`. `PAYMENTS_SANDBOX=true` и `scripts/sandbox-e2e.sh` этот gate не открывают.

### 9. Обновление уже установленной копии

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

Скрипт скачивает последний релиз GitHub, проверяет SHA-256 и вызывает `scripts/update.sh`. Снимок `pre-update-<дата>.tar.gz` и дамп `pg_dump` создаются до копирования файлов. `.env` в архив не входит и на диске остаётся. Cron этот скрипт не включает.

---

# Step-by-step install — Remnawave VPN Shop 3.1.6

This file is the from-scratch install. Each prompt below is the prompt in `deploy/install-vps.sh`. The staging E2E panel and **Разрешить реальные платежи** (Allow live payments) are in section 9.15 of `INSTRUCTION.md`.

## English

### 1. What gets installed

On Debian or Ubuntu the script installs Docker Engine and Docker Compose, copies the project to `/opt/vpn-shop`, writes `.env` as mode `0600`, builds the images, and starts PostgreSQL 16, Redis 7, the API, the worker, the bot, the admin UI, the Mini App, the user cabinet, and Caddy. Alembic migrates to `0038_v2_6_0_platform`. The installer version is **3.1.6**. The admin UI, Mini App, and cabinet answer HTTP, and nginx writes under `/tmp/nginx`. The prompts are the same as in **3.1.5**, **3.1.4**, **3.1.3**, **3.1.2**, and **3.1.1**. Surrounding spaces are removed. `Moscow` is stored as `Europe/Moscow`.

The firewall keeps SSH, TCP 80, TCP 443, and UDP 443. PostgreSQL, Redis, the API, and the panels stay unpublished. Caddy serves them on their own domains.

### 2. Prepare this before the command

1. A clean Debian or Ubuntu VPS with root SSH.
2. DNS A records (and AAAA records if you use IPv6) already pointing at this VPS. The certificate is issued after that.
3. A BotFather token and the bot username without `@`.
4. An `https://` Remnawave panel URL and that panel’s API token.
5. Live YooKassa, Platega, or RollyPay credentials when you want a cashier. `none` is valid for the first boot: the shop starts, and live charges stay closed until section 9.15.
6. An administrator email and a password of at least 12 characters. An empty password becomes `openssl rand -hex 16` and is printed once at the end.

The staging E2E fields are not in this questionnaire. These answers are the shop credentials. Sandbox cashier keys are entered later in the panel and must differ from the `.env` values.

### 3. Domain names

For a base domain `vpn.example.com` the script suggests:

| Prompt | Default |
| --- | --- |
| API domain | `api.vpn.example.com` |
| Admin domain | `admin.vpn.example.com` |
| Mini App domain | `app.vpn.example.com` |
| Cabinet domain | `cabinet.vpn.example.com` |
| Webhook domain | `pay.vpn.example.com` |
| Bot domain | `bot.vpn.example.com` |

Create a DNS record for every name you keep. `PANEL_DOMAIN` defaults to the base domain and matters when Caddy should also publish the Remnawave panel.

### 4. Start

From a downloaded release directory on the server:

```bash
sudo bash install.sh
```

From GitHub on a clean server:

```bash
curl -fsSL https://raw.githubusercontent.com/booarkz-cpu/remnawave-vpn-shop/main/install.sh | sudo bash
```

`install.sh` checks for root, installs `ca-certificates`, `curl`, `git`, `openssl`, and Docker, then execs `deploy/install-vps.sh`. A `curl` launch clones branch `main` into `/opt/vpn-shop-src`. A launch from the project directory uses that directory. If `/opt/vpn-shop` already has `docker-compose.yml` or `.env`, the script stops and asks you to update the existing copy.

The `curl | bash` pipe is occupied by the script text, so questions are read from the SSH terminal (`/dev/tty`). In **3.1.2** the first question on that pipe ended with `installation failed at line 34`. From **3.1.3** the same command waits for the answer in the terminal. Without a terminal, set `INSTALL_NONINTERACTIVE=1` and the environment variables.

### 5. Answers, in order

The script states that DNS must already point at this VDS, then asks:

1. `Основной домен (например vpn.example.com)` — required base domain.
2. `API-домен` — Enter keeps `api.<base>`.
3. `Домен админки` — Enter keeps `admin.<base>`.
4. `Домен Mini App` — Enter keeps `app.<base>`.
5. `Домен личного кабинета` — Enter keeps `cabinet.<base>`.
6. `Email администратора` — Enter keeps `admin@<base>`.
7. `Пароль администратора (Enter = сгенерировать)` — hidden. Enter generates the password at the end.
8. `Telegram BOT_TOKEN от @BotFather` — required, hidden.
9. `Remnawave Panel URL` — required `https://` panel URL.
10. `Remnawave API token` — required, hidden.
11. `Провайдер (yookassa / platega / rollypay / none)` — default `none`.
12. For `yookassa`: `YooKassa Shop ID` and a hidden `YooKassa Secret Key`.
13. For `platega`: `Platega Merchant ID` and a hidden `Platega Secret`.
14. For `rollypay`: hidden `RollyPay API Key` and `RollyPay Signing Secret`.
15. Extra cashiers. For providers not chosen in step 11, the script asks for the Shop ID, Merchant ID, or API Key. The secret is asked only when that identifier is non-empty. Enter leaves the field empty.
16. `Platega refund URL` and `RollyPay refund URL`. Empty is valid until that cashier must refund.
17. `Имя бота без @` — required bot username.
18. `Telegram ID администратора (@userinfobot)` — numeric id. Empty leaves `/ops` unbound.
19. `Язык по умолчанию (ru/en)` — default `ru`. Any other value is rejected.
20. `Валюта` — default `RUB`.
21. `Часовой пояс` — default `Europe/Moscow`.
22. `Email для TLS-сертификата` — default is the administrator email.
23. `Домен вебхуков` — default `pay.<base>`.
24. `Домен Mini App, если отличается` — default is the Mini App domain from step 4.
25. `Домен бота` — default `bot.<base>`.
26. `Домен панели Remnawave в Caddy, если нужен` — default is the base domain.
27. Prices: 1 month `199`, 3 months `499`, 6 months `899`, 12 months `1499`.
28. `Автопродление (true/false)` — default `false`.
29. `За сколько дней до конца списывать автопродление` — default `3`.
30. `Обязательный канал` — Enter leaves the required channel off.
31. `Telegram-чат алертов` — alert chat, may be empty.
32. `Процент реферального вознаграждения` — default `5.0`.
33. `За сколько дней предупреждать об окончании` — default `3`.
34. Yandex OAuth client id and hidden secret. Enter skips Yandex sign-in.
35. VK OAuth client id and hidden secret. Enter skips VK sign-in.
36. `Песочница платежей без шлюзов (true/false)` — default `false`. `true` sets `PAYMENTS_SANDBOX` for `scripts/sandbox-e2e.sh`. That flag does not open the production gate.
37. `Максимум дней пробного периода` — default `3`.
38. `S3 endpoint`. Enter disables off-site backup. When the endpoint is set, fill the bucket, region (default `auto`), access key, and hidden secret key.

The script then generates `APP_SECRET` and the PostgreSQL password, configures UFW and Fail2Ban for SSH, pins base-image digests, builds the frontend lockfiles, builds the containers, and waits for `GET /health` inside the `backend` container.

### 6. Install without prompts

Export the variables and start:

```bash
export INSTALL_NONINTERACTIVE=1
export BASE_DOMAIN=vpn.example.com
export ADMIN_EMAIL=admin@vpn.example.com
export ADMIN_PASSWORD='replace-with-your-password'
export BOT_TOKEN='token-from-BotFather'
export REMNAWAVE_URL='https://panel.example.com'
export REMNAWAVE_TOKEN='remnawave-token'
export BOT_USERNAME='bot_username_without_at'
export PAYMENT_PROVIDER=none
sudo --preserve-env bash install.sh
```

An empty required variable stops the script with `Не задано обязательное поле`. Every other name takes the default from section 5: `API_DOMAIN`, `ADMIN_DOMAIN`, `APP_DOMAIN`, `CABINET_DOMAIN`, `DEFAULT_LANGUAGE`, `DEFAULT_CURRENCY`, `TZ_VALUE`, `CADDY_EMAIL`, `WEBHOOK_DOMAIN`, `PRICE_1`, `PRICE_3`, `PRICE_6`, `PRICE_12`, `AUTO_RENEW_ENABLED`, `AUTO_RENEW_LEAD_DAYS`, `REFERRAL_REWARD_PERCENT`, `NOTIFICATION_EXPIRY_DAYS`, `PAYMENTS_SANDBOX`, `TRIAL_MAX_DAYS`.

### 7. Check the install immediately

The script prints Admin, Mini App, Cabinet, and API URLs, version `3.1.6`, and the administrator email. A generated password is the line `Admin password (generated)`. Store it off the server and turn on 2FA under **Безопасность** (Security).

```bash
curl -fsS "https://api.YOUR-DOMAIN/health"
cd /opt/vpn-shop
docker compose ps
./scripts/doctor.sh
```

`/health` returns `"ok": true`, `"version": "3.1.6"`, `"database": true`, and `"redis": true`. The previous release answered `"version": "3.1.5"`. Release **3.1.4** answered `"version": "3.1.4"`. Release **3.1.3** answered `"version": "3.1.3"`. Release **3.1.2** answered `"version": "3.1.2"`. The check command is `curl -fsS`, not `url`. `docker compose ps` should show `admin`, `miniapp`, and `cabinet` as `Up`, not `Restarting`. `doctor.sh` expects `/opt/vpn-shop` and a running Docker engine.

Open `https://admin.<domain>` and sign in. Create one enabled plan: its numeric id is required for staging E2E.

The installer writes a starter `YOOKASSA_WEBHOOK_IP_ALLOWLIST`. Compare it with the provider’s current network list and set the cashier webhook to `https://pay.<domain>`. An empty list answers 403 `Webhook IP not allowed`.

### 8. Staging E2E and the production gate

Signed in as role `admin`:

1. Open **Проверка тестового контура** (Staging checks).
2. Fill the shop’s public HTTPS URL, the staging Remnawave HTTPS URL, the staging token, and the test plan id.
3. Enable only cashiers that have sandbox keys. Enter those keys here, not in `.env`.
4. Check **Подтверждаю sandbox-ключи** (I confirm these are sandbox keys) and press **Сохранить безопасную конфигурацию** (Save the safe configuration).
5. Press **Запустить staging E2E** (Run staging E2E) and open the `[CHECKOUT]` lines in the card log.
6. **Разрешить реальные платежи** (Allow live payments) on **Безопасность** (Security) accepts the enable when the log contains `FULL_E2E_PASS` and `finished_at` is younger than 24 hours.

The full order, the 409 answers, and the meaning of `awaiting_checkout` are in section 9.15 of `INSTRUCTION.md`. `PAYMENTS_SANDBOX=true` and `scripts/sandbox-e2e.sh` do not open this gate.

### 9. Update an existing install

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

The script downloads the latest GitHub release, checks SHA-256, and runs `scripts/update.sh`. The `pre-update-<date>.tar.gz` snapshot and the `pg_dump` are taken before files are copied. `.env` stays out of the archive and stays on disk. The script does not install cron.
