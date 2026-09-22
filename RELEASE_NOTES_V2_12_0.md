# Remnawave VPN Shop 2.12.0

Лицензия: Remnawave VPN Shop Proprietary License 1.0, файл `LICENSE`, `SPDX-License-Identifier: LicenseRef-Proprietary`.

Схема базы: `0038_v2_6_0_platform`. Новой миграции нет. Таблица `broadcasts` создана миграцией `0003_marketing`.

## Русский

### Что изменилось

Веб-панель уже умела поставить одну HTML-рассылку на всех пользователей с Telegram. В 2.12.0 эта же очередь доступна в приложениях администратора Android и iOS. В панели выбирается аудитория, кнопка и картинка. Воркер бота сохраняет прогресс после каждого получателя, помечает обрыв как `failed` и по кнопке «Повторить» продолжает список, а не начинает его заново.

Приложение покупателя не менялось и остаётся **2.10.0**. Приложение администратора Android: `versionName` **2.12.0**, `versionCode` **2120**, пакет `shop.remnawave.admin`, User-Agent `RemnawaveShop-Android-Admin/2.12.0`. iOS-администратор: `MARKETING_VERSION` **2.12.0**, `CURRENT_PROJECT_VERSION` **2120**, User-Agent `RemnawaveShop-iOS-Admin/2.12.0`. Исторические строки 2.10.0 и 2.9.0 остаются в исходниках как маркеры совместимости. Новая строка User-Agent начинает новую сессию: старая сессия к ней не привязана.

Обновление проекта с GitHub остаётся командой `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`. Снимок и `pg_dump` по-прежнему снимаются до копирования файлов. Это поведение 2.11.0.

### Как отправить рассылку

1. Заполните `BOT_TOKEN` и убедитесь, что процесс бота запущен. API только пишет строку в `broadcasts`. Сообщение в Telegram отправляет `broadcast_worker`.
2. Войдите как оператор или администратор. Право — `manage_broadcasts`. Наблюдатель видит историю и получает 403 на создание.
3. В веб-панели откройте **Маркетинг**. В приложении откройте вкладку **Рассылка**.
4. Выберите аудиторию:
   - все с Telegram;
   - активная подписка (`expires_at` в будущем);
   - без активной подписки.
5. Введите HTML-текст до 4000 символов. Кнопку задавайте парой: текст и абсолютный HTTPS URL. Картинку — отдельным HTTPS URL. С картинкой текст не длиннее 1024 символов.
6. Нажмите «Отправить в очередь». Статус проходит `queued` → `sending` → `completed`. Счётчики `sent_count` и `failed_count` видны в истории и в `GET /api/admin/marketing`.
7. Если процесс бота остановился во время отправки, статус становится `failed`. «Повторить» возвращает строку в `queued` и пропускает уже посчитанных получателей. Завершённую рассылку повтор не перезапускает: создайте новую.

### Исправления этого выпуска

- Активная аудитория больше не отправляет одно сообщение несколько раз, если у пользователя несколько подписок. Запрос получателей использует `distinct`.
- Обрыв воркера не оставляет строку в `sending` навсегда: статус становится `failed`, повтор доступен администратору.
- Прогресс пишется после каждого получателя. Повтор продолжает с `sent_count + failed_count` в порядке `id`.
- Ответ Telegram 429 повторяется один раз, с паузой из `retry_after`, не дольше 30 секунд.
- HTTP-клиент рассылки не читает прокси из окружения (`trust_env=False`), как и остальные исходящие вызовы к Telegram.
- Кнопка без URL или URL без текста отклоняется. Подпись длиннее 1024 символов при наличии картинки отклоняется до постановки в очередь.
- В панели аудитория больше не зашита как `all`.

### Границы

Повтор опирается на стабильный порядок `id`. Если между попытками пользователя удалили, окно пропуска может сдвинуться на одного человека. Отдельной таблицы получателей нет, миграция не добавлялась. Уже доставленное сообщение Telegram повторно не отзывается.

Живые YooKassa, Platega, RollyPay, панель Remnawave и Docker Compose на машине сборки этого выпуска не запускались. iOS IPA не собран: нужен Xcode на macOS. Проверка выпуска — `pytest`, разбор Python, `bash -n`, сборка Vite админки и, когда менялось приложение администратора, release APK Android.

### Разбор функций

#### Магазин покупателя

| Функция | Как работает |
| --- | --- |
| Вход | Telegram initData проверяется HMAC. Email и пароль используют scrypt. VK и Яндекс включаются переменными окружения. Сессия браузера — HttpOnly cookie `rw_user`. Приложение с `X-Shop-Client` получает `access_token` и cookie не хранит. |
| Тарифы | `GET /api/plans` отдаёт включённые тарифы. Якорный тариф конструктора в этом списке скрыт. |
| Конструктор | Покупатель выбирает устройства, трафик и дни. Цена = база + пункты. Снимок пишется в платёж и не меняется при правке конструктора. |
| Оплата | `POST /api/payments/create` требует `Idempotency-Key`. Намерение пишется до вызова кассы. Повтор того же ключа с другим тарифом отвечает 409. Условие `if existing.plan_id != plan_id` сохранено. |
| Кошелёк | `POST /api/me/wallet/spend` тоже требует ключ идемпотентности. Пополнение `POST /api/me/wallet/topup` принимает сумму 50–100000. Провайдер `sandbox` работает при `PAYMENTS_SANDBOX=true`. |
| Выдача | `fulfill` под блокировкой пользователя и платежа создаёт или продлевает доступ в Remnawave. Повтор той же операции срок второй раз не прибавляет. |
| Пробный период | Доступен, пока пользователь не ограничен. `users.restricted_at` отвечает 403 «Доступ ограничен». |
| Подарок | `POST /api/me/gifts/redeem` принимает код длиной 4–64. Бот умеет deep-link `GIFT_`. |
| Подключение | `GET /api/me/connection-qr` отдаёт PNG. Ссылки Happ, v2rayNG и Streisand строятся только из `https://` без пробелов. |
| Устройства | Список не содержит `device_key` и `last_ip`. Чёрный список HWID отвечает 403 «Устройство в чёрном списке». |
| Трафик | Если панель не ответила, лимит берётся из снимка платежа. |
| Подпись приложения | Для известных `X-Shop-Client` при `MOBILE_REQUIRE_PROOF` проверяются `X-Shop-Time` и `X-Shop-Proof`. Окно 300 секунд. Путь без query. Ошибка: «Подпись клиента не принята». |

#### Администратор

| Функция | Как работает |
| --- | --- |
| Вход | Пароль scrypt, необязательный TOTP или код восстановления. JWT связан с `AdminSession` и User-Agent. Простой дольше 15 минут завершает сессию. Веб-вход не кладёт JWT в JSON. Приложение администратора его получает. |
| Роли | `viewer` читает. `operator` ведёт тарифы, пользователей, платежи кроме возвратов, контент, рассылки и поддержку. `admin` добавляет администраторов, возвраты, бэкапы и сессии. |
| Рассылка | Описана выше. Аудит: `marketing.broadcast.queued` и `marketing.broadcast.retried`. |
| Тариф | `POST /api/admin/plans/{id}/enabled` требует `manage_plans`. |
| Платёж | `GET /api/admin/payments/{id}` не отдаёт текст ошибки выдачи, URL кассы и id платежа у провайдера. |
| Узлы | Публичный и пользовательский ответ содержит имя, страну, статус и число онлайн. Адреса, токены и текст исключения не отдаются. |
| Агенты | Агент без `last_seen_at` или старше 5 минут помечается `stale`. На узле допустимы только `throttle` и `clear`, и только при `AGENT_APPLY_TC=1`. |
| Платформа | Скоринг, чёрный список HWID, ключи API, исходящие webhook. Секрет показывается один раз. |
| Кабинет | CMS вкладок, логотип `client_logo`, каталог приложений. Публичный `GET /api/public/apps` отдаёт только включённые карточки покупателя. |
| Релизы | `GET /api/admin/github-update` показывает статус. Архив API не распаковывает. |
| Бэкап | Архив в `BACKUPS_DIR`. Восстановление требует подтверждение и, при включённой 2FA, одноразовый код. |

#### Бот и обновление

| Функция | Как работает |
| --- | --- |
| `/start` | Приветствие на языке Telegram, цены, акции, кнопка Mini App. Картинка приветствия не ломает ответ, если Telegram её не принял. |
| `/promo` | Открывает магазин с кодом. Сервер проверяет код ещё раз при оплате. |
| `/ops` | Только для `ADMIN_TELEGRAM_ID`. Показывает открытые нарушения и агентов за 5 минут. |
| Обновление | `scripts/github_release_fetch.py` принимает архив не больше 80 МБ, отклоняет чужой хост, symlink и путь с `..`. `scripts/update.sh` исключает `.env` и `.env.*`. |

### Проверка

На машине сборки выполняются `python -m pytest`, `python -m compileall backend`, `bash -n` для скриптов установщика и сборка Vite админки. Release APK администратора подписывается ключом, который в git не входит. Контрольная сумма публикуется рядом с файлом, в строке — имя файла, не абсолютный путь.

### Установка поверх 2.11.0

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

`.env` сохраняется. После обновления перезапускаются API, worker и bot. Рассылка заработает, когда процесс бота снова читает очередь.

## English

License: Remnawave VPN Shop Proprietary License 1.0, file `LICENSE`, `SPDX-License-Identifier: LicenseRef-Proprietary`.

Database schema: `0038_v2_6_0_platform`. There is no new migration. The `broadcasts` table comes from migration `0003_marketing`.

### What changed

The web panel could already queue one HTML broadcast to every user with Telegram. In 2.12.0 the same queue is available in the Android and iOS administrator apps. The panel selects the audience, a button and an image. The bot worker saves progress after each recipient, marks a crash as `failed`, and the Retry button continues the list.

The buyer app is unchanged and stays **2.10.0**. The Android administrator app uses `versionName` **2.12.0**, `versionCode` **2120**, package `shop.remnawave.admin`, User-Agent `RemnawaveShop-Android-Admin/2.12.0`. The iOS administrator app uses `MARKETING_VERSION` **2.12.0**, `CURRENT_PROJECT_VERSION` **2120**, User-Agent `RemnawaveShop-iOS-Admin/2.12.0`. The historical 2.10.0 and 2.9.0 strings remain in source as compatibility markers. A new User-Agent starts a new session.

The GitHub update command is still `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`. The snapshot and `pg_dump` still run before files are copied. That is the 2.11.0 behavior.

### How to send a broadcast

1. Set `BOT_TOKEN` and keep the bot process running. The API only inserts a `broadcasts` row. `broadcast_worker` sends the Telegram message.
2. Sign in as an operator or an administrator. The permission is `manage_broadcasts`. A viewer can read history and receives 403 on create.
3. In the web panel open **Маркетинг** (Marketing). In the app open the **Рассылка** (Broadcast) tab.
4. Choose the audience: everyone with Telegram, an active subscription (`expires_at` in the future), or no active subscription.
5. Enter HTML up to 4000 characters. A button is a pair: text and an absolute HTTPS URL. An image is a separate HTTPS URL. With an image the text stays within 1024 characters.
6. Choose «Отправить в очередь» (Queue broadcast). The status moves `queued` → `sending` → `completed`. `sent_count` and `failed_count` appear in the history and in `GET /api/admin/marketing`.
7. If the bot process stops during delivery, the status becomes `failed`. Retry returns the row to `queued` and skips recipients already counted. Retry does not restart a completed broadcast. Create a new row for a new send.

### Fixes in this release

- The active audience no longer sends one message several times when a user has several subscriptions. The recipient query uses `distinct`.
- A worker crash does not leave the row in `sending` forever. The status becomes `failed`, and an administrator can retry.
- Progress is stored after each recipient. Retry continues from `sent_count + failed_count` in `id` order.
- A Telegram 429 is retried once, using `retry_after`, and never waits longer than 30 seconds.
- The broadcast HTTP client ignores proxy environment variables (`trust_env=False`), matching the other Telegram calls.
- A button without a URL, or a URL without text, is rejected. A caption longer than 1024 characters with an image is rejected before the row is queued.
- The panel audience is no longer fixed to `all`.

### Limits

Retry depends on a stable `id` order. If a user is deleted between attempts, the skip window can move by one person. There is no recipient table and no new migration. A message Telegram already delivered is not recalled.

Live YooKassa, Platega, RollyPay, the Remnawave panel and Docker Compose were not started on the build machine for this release. The iOS IPA is not built: that needs Xcode on macOS. The release check is `pytest`, Python compilation, `bash -n`, the admin Vite build and, because the administrator app changed, a release-signed Android APK.

### Function reference

#### Buyer shop

| Function | Behavior |
| --- | --- |
| Sign-in | Telegram initData is checked with HMAC. Email and password use scrypt. VK and Yandex turn on through environment variables. A browser session is the HttpOnly cookie `rw_user`. An app with `X-Shop-Client` receives `access_token` and does not store the cookie. |
| Plans | `GET /api/plans` returns enabled plans. The constructor anchor plan is hidden from that list. |
| Constructor | The buyer picks devices, traffic and days. Price = base + options. The snapshot is stored on the payment and does not change when the constructor is edited later. |
| Payment | `POST /api/payments/create` requires `Idempotency-Key`. The intent is stored before the provider call. The same key with another plan returns 409. The condition `if existing.plan_id != plan_id` stays in place. |
| Wallet | `POST /api/me/wallet/spend` also requires an idempotency key. Top-up `POST /api/me/wallet/topup` accepts 50–100000. Provider `sandbox` works when `PAYMENTS_SANDBOX=true`. |
| Fulfillment | `fulfill` creates or extends Remnawave access under a user lock and a payment lock. Repeating the same operation does not add the term twice. |
| Trial | Available until the user is restricted. `users.restricted_at` returns 403 «Доступ ограничен». |
| Gift | `POST /api/me/gifts/redeem` accepts a code of 4–64 characters. The bot accepts a `GIFT_` deep link. |
| Connection | `GET /api/me/connection-qr` returns a PNG. Happ, v2rayNG and Streisand links are built only from `https://` with no spaces. |
| Devices | The list omits `device_key` and `last_ip`. An HWID blacklist returns 403 «Устройство в чёрном списке». |
| Traffic | When the panel does not answer, the limit comes from the payment snapshot. |
| App proof | Known `X-Shop-Client` values are checked with `X-Shop-Time` and `X-Shop-Proof` when `MOBILE_REQUIRE_PROOF` is on. The window is 300 seconds. The path has no query. The error is «Подпись клиента не принята». |

#### Administrator

| Function | Behavior |
| --- | --- |
| Sign-in | scrypt password, optional TOTP or a recovery code. The JWT is bound to `AdminSession` and the User-Agent. Idle time beyond 15 minutes ends the session. A web login does not put the JWT in JSON. The administrator app receives it. |
| Roles | `viewer` reads. `operator` manages plans, users, payments except refunds, content, broadcasts and support. `admin` also manages administrators, refunds, backups and sessions. |
| Broadcast | Described above. Audit actions: `marketing.broadcast.queued` and `marketing.broadcast.retried`. |
| Plan | `POST /api/admin/plans/{id}/enabled` requires `manage_plans`. |
| Payment | `GET /api/admin/payments/{id}` omits the fulfillment error text, the checkout URL and the provider payment id. |
| Nodes | A public or buyer response contains name, country, status and online users. Addresses, tokens and exception text are omitted. |
| Agents | An agent with no `last_seen_at`, or one older than 5 minutes, is `stale`. On the node only `throttle` and `clear` are allowed, and only when `AGENT_APPLY_TC=1`. |
| Platform | Scoring, HWID blacklist, API keys, outbound webhooks. A secret is shown once. |
| Cabinet | Tab CMS, `client_logo`, app catalog. Public `GET /api/public/apps` returns enabled buyer cards only. |
| Releases | `GET /api/admin/github-update` shows status. The API does not extract archives. |
| Backup | The archive lives in `BACKUPS_DIR`. Restore requires confirmation and, when 2FA is on, a one-time code. |

#### Bot and update

| Function | Behavior |
| --- | --- |
| `/start` | Greeting in the Telegram language, prices, promotions, Mini App button. A rejected welcome image does not break the reply. |
| `/promo` | Opens the shop with the code. The server checks the code again at payment time. |
| `/ops` | Only for `ADMIN_TELEGRAM_ID`. Shows open violations and agents seen in 5 minutes. |
| Update | `scripts/github_release_fetch.py` accepts an archive up to 80 MB and rejects another host, a symlink and a `..` path. `scripts/update.sh` excludes `.env` and `.env.*`. |

### Check

The build machine runs `python -m pytest`, `python -m compileall backend`, `bash -n` for the installer scripts and the admin Vite build. The administrator release APK is signed with a key that is not in git. The checksum is published next to the file, and the checksum line uses the file name.

### Install over 2.11.0

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

`.env` is kept. After the update, restart the API, the worker and the bot. The broadcast runs when the bot process reads the queue again.
