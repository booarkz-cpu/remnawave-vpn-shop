# Полная инструкция — Remnawave VPN Shop 2.2.1

Документ для оператора, который ставит магазин, включает платежи и сопровождает панель. Разбор каждой функции кода — в `FUNCTIONS.md`. Модель безопасности — в `SECURITY.md`.

---

## 1. Что это

Магазин VPN: Telegram-бот, Mini App, админ-панель и API. Покупатель выбирает тариф, оплачивает через YooKassa, Platega или RollyPay. После подтверждения оплаты API создаёт или продлевает пользователя в Remnawave. Фоновый worker дожимает очередь выдачи, сверки и уведомления.

Сервисы Docker Compose: `db` (PostgreSQL 16), `redis`, `backend` (FastAPI), `worker`, `bot`, `admin`, `miniapp`, `caddy`. PostgreSQL и Redis наружу не публикуются. Снаружи открыты порты Caddy: TCP 80, TCP 443, UDP 443.

Интерфейс админки, Mini App и ответы бота работают на русском и английском.

## 2. Требования

- Debian или Ubuntu с root для `install.sh`, либо любой хост с Docker Engine и Docker Compose plugin.
- Домен с DNS на этот сервер, если нужен HTTPS через Caddy. Для локальной проверки допустимы `localhost`.
- Доступ к панели Remnawave: URL и API-токен.
- Токен бота от @BotFather и публичный HTTPS URL Mini App.
- Для боевых платежей: магазин выбранного провайдера и, для YooKassa, список доверенных IP вебхуков.

`APP_SECRET` не короче 32 символов. Пароль администратора в примере — не короче 12 символов. Пароль PostgreSQL в `.env.example` ограничен буквами и цифрами, чтобы он совпал в `DB_PASSWORD`, `POSTGRES_PASSWORD` и `DATABASE_URL`.

## 3. Установка одной командой

На чистом Debian/Ubuntu:

```bash
sudo bash install.sh
```

Скрипт сам ставит Docker, спрашивает данные, которые нельзя угадать, генерирует `APP_SECRET` и пароль базы, пишет `.env` с правами `0600`, собирает образы, поднимает PostgreSQL и Redis, применяет миграции Alembic и печатает адреса панели, Mini App и API. Он настраивает UFW (SSH, TCP 80/443, UDP 443) и Fail2Ban для SSH.

`install.sh` — самостоятельный установщик. Каталог `deploy/` содержит Caddyfile и вспомогательные скрипты, отдельный `deploy/install-vps.sh` этим установщиком не вызывается.

После установки каталог проекта обычно `/opt/vpn-shop`. Проверки:

```bash
cd /opt/vpn-shop
./scripts/preflight.sh
./scripts/security-scan.sh
./scripts/doctor.sh
```

Обновление и откат:

```bash
./scripts/update.sh
./scripts/rollback.sh
```

2FA после установки выключена. Включите её в панели: **Безопасность**.

## 4. Установка через Docker Compose

```bash
cp .env.example .env
```

Заполните обязательные поля: `APP_SECRET`, `DB_PASSWORD` (тот же пароль в `POSTGRES_PASSWORD` и в `DATABASE_URL`), `BOT_TOKEN`, `BOT_USERNAME`, `REMNAWAVE_URL`, `REMNAWAVE_TOKEN`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, домены `API_DOMAIN`, `ADMIN_DOMAIN`, `APP_DOMAIN` и публичные URL `PUBLIC_BASE_URL`, `MINI_APP_URL`. Для YooKassa заполните `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY` и непустой `YOOKASSA_WEBHOOK_IP_ALLOWLIST`.

```bash
docker compose up -d --build
docker compose ps
```

Compose сам задаёт контейнерам `MEDIA_DIR=/data/media`, `BACKUPS_DIR=/data/backups`, `PROJECT_DIR=/project`. Эти значения перекрывают `.env`. Тома: `media_data`, `backup_data`, каталог проекта смонтирован в `/project` только для чтения. Backend и worker работают с `read_only: true` и tmpfs на `/tmp`.

Проверка живости API внутри сети compose: `GET /health` на порту 8000 контейнера `backend`.

## 5. Локальный запуск без контейнеров

Нужны Python 3.12, Node.js, PostgreSQL и Redis. Укажите записываемые каталоги: процесс создаёт `MEDIA_DIR` при импорте приложения. Значения по умолчанию `/data/media`, `/data/backups` и `/project` рассчитаны на Docker. На хосте без этих путей задайте, например, `MEDIA_DIR=./data/media`.

Миграции:

```bash
cd backend
alembic upgrade head
```

Сборка интерфейсов:

```bash
cd admin && npm ci && npx vite build
cd miniapp && npm install && npx vite build
```

Проверка исходников:

```bash
python3 -m compileall -q backend
python3 -m pytest -q
```

Тесты в `tests/` в основном сверяют исходный текст контрактов. Они не поднимают живые кассы и Remnawave.

## 6. Переменные, без которых панель не работает как магазин

Полный список с комментариями — `.env.example`. Ниже только то, что меняет поведение этой версии.

| Переменная | Смысл |
| --- | --- |
| `APP_SECRET` | Подпись JWT и шифрование TOTP, кодов восстановления и staging-конфига. Минимум 32 символа. |
| `APP_SECRET_PREVIOUS` | Только на время ротации ключа. Потом очистите. |
| `APP_ENV` | `production` или `development`. |
| `DEFAULT_LANGUAGE` | `ru` или `en`. Язык бота и стартовый язык Mini App, пока человек не выбрал свой. |
| `MAINTENANCE_MODE` | `true` отклоняет создание платежей на уровне процесса, до чтения настройки из базы. |
| `BOT_TOKEN`, `BOT_USERNAME` | Бот Telegram. |
| `ADMIN_TELEGRAM_ID` | Telegram ID администратора для алертов и входа, где он используется. |
| `REMNAWAVE_URL`, `REMNAWAVE_TOKEN` | Панель Remnawave. |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Первый администратор. |
| `ADMIN_CORS_ORIGINS` | Список origin через запятую. |
| `COOKIE_SECURE`, `COOKIE_SAMESITE` | Для HTTPS и Telegram WebApp обычно `true` и `none`. |
| `YOOKASSA_WEBHOOK_IP_ALLOWLIST` | Обязателен, если принимаете вебхуки YooKassa. Пустой список отклоняет вебхук. |
| `PLATEGA_*`, `ROLLYPAY_*` | Секреты и URL возврата выбранного провайдера. |
| `AUTO_RENEW_ENABLED` | Автопродление сохранённым способом YooKassa. По умолчанию выключено. |
| `BACKUP_S3_*`, `S3_*` | Внешняя копия бэкапа. Префикс объектов — `BACKUP_S3_PREFIX` (`vpn-shop`). |
| `METRICS_TOKEN` | Закрывает `/metrics`. Пустое значение не публикуйте наружу. |
| `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET`, `YANDEX_REDIRECT_URI` | Все три нужны, чтобы включить вход Yandex ID. Пустые поля оставляют провайдер выключенным. |
| `MEDIA_DIR`, `BACKUPS_DIR`, `PROJECT_DIR` | Каталоги медиа, архивов и исходников. В Compose задаются сервисом. |

Боевые платежи остаются закрыты, пока администратор не пройдёт staging E2E и не включит production gate в панели. Staging-запрос использует только переданные тестовые ключи и не читает боевые секреты провайдеров.

## 7. Первый вход администратора

1. Откройте админку по `ADMIN_DOMAIN` (локально — адрес, который напечатал установщик или Caddy).
2. Введите `ADMIN_EMAIL` и `ADMIN_PASSWORD`. Поле TOTP оставьте пустым, пока 2FA выключена.
3. После входа откройте **Безопасность**, запустите настройку 2FA, сохраните коды восстановления и подтвердите код из приложения-аутентификатора.
4. В **Тарифы** создайте хотя бы один включённый тариф: название, цена, срок в днях.
5. В **Бот и Mini App** проверьте имя бота, ссылку Mini App (`https://`) и меню.
6. В **Провайдеры** включите только те кассы, чьи ключи заполнены.
7. Сделайте тестовый платёж в **Проверка тестового контура**, затем включите разрешение реальных платежей.
8. В **Бекапы** задайте расписание и пароль шифрования и запустите первую копию.

Сессия администратора — cookie `rw_admin` (HttpOnly). Она привязана к User-Agent, гаснет после 15 минут простоя и не живёт дольше срока токена. Мутации требуют заголовок `X-CSRF-Token`, равный cookie `rw_csrf`. Кнопка **Завершить все** в разделе **Сессии** отзывает все сессии текущего администратора.

Вход через Telegram на форме входа работает, только если панель открыта внутри Telegram WebApp и initData проходит проверку.

## 8. Язык интерфейса

Кнопка языка в шапке админки и Mini App переключает `RU` и `EN`. Выбор пишется в `localStorage` ключ `rw_lang`. Пока ключа нет:

- админка смотрит язык браузера;
- Mini App после загрузки `/api/public/config` берёт `default_language` сервера (`DEFAULT_LANGUAGE`), если браузерный запасной вариант не сохранён;
- бот смотрит `language_code` Telegram, иначе `DEFAULT_LANGUAGE`.

Русский текст остаётся в исходниках интерфейса. Английский подставляется после отрисовки словарём `admin/src/i18n.tsx` и `miniapp/src/i18n.tsx`. Диалоги `prompt` и `confirm` переводятся тем же словарём. Данные в базе, имена тарифов и тексты рассылок язык интерфейса не переводит.

## 9. Разделы админ-панели

Роли: `viewer`, `operator`, `admin`. Недостаточное право отвечает HTTP 403. Зритель читает пользователей, платежи, маркетинг, аналитику и поддержку и управляет своей 2FA. Оператор ведёт тарифы, пользователей, платежи без возврата, контент, рассылки, поддержку, диагностику, инциденты, провайдеров и флаги. Администратор дополнительно управляет другими администраторами, бэкапами, возвратами, сверкой, staging E2E, сессиями и выплатами рефералов.

| Раздел | Что делать |
| --- | --- |
| Брендинг панели | Название, логотип, favicon, тема по умолчанию. Файл перекодируется на сервере. Старый файл удаляется по basename внутри `MEDIA_DIR`. |
| Обзор | Пользователи, активные VPN, выручка, ошибки выдачи, состояние API, Redis и Remnawave. |
| Корпоративный контур | Проверки мониторинга, кампании, правила, сводка устройств. Новые правила создаются выключенными. |
| Сессии | Список сессий администраторов, завершение одной или всех своих. |
| Тарифы | Создание и удаление тарифа. Цена и срок уходят в каталог Mini App. |
| Платежи | Список намерений, статус оплаты и выдачи, повтор неуспешной выдачи, кнопка сверки. |
| Финансовый журнал | Проводки выручки, возвратов и реферальных начислений. |
| Пользователи | Карточки покупателей и подписок. |
| Бот и Mini App | Имя бота, стартовая картинка, пункты меню, поля, объявления. Ссылки меню принимаются только с `https://`. |
| Маркетинг | Акции и промокоды, сроки и привязка к тарифам. |
| Администраторы | Создание учёток с ролью `viewer`, `operator` или `admin`. |
| Бекапы | Расписание 6/12/24 часа или выключено, срок хранения, пароль, запуск, проверка и восстановление. |
| Безопасность | 2FA, коды восстановления, индикатор production gate. |
| Центр восстановления | Сердцебиение worker, зависшие задачи, аварийные действия. |
| Аудит | Журнал действий администраторов. |
| Поддержка | Тикеты покупателей. |
| Возвраты | Запрос возврата у провайдера и отзыв VPN, если нет более новой оплаченной выдачи. |
| Рабочие процессы | Состояние worker fleet. |
| Релизы | Канал обновлений и откат. Перед боем проверьте подпись манифеста, если задан `RELEASE_MANIFEST_PUBLIC_KEY`. |
| Мониторинг | Метрики API, диск, свежесть бэкапа, ошибки выдачи. |
| Очередь задач | `queued`, `processing`, `completed`, `failed`, попытки и срок аренды. |
| Антифрод | Сигналы скорости. Один слабый сигнал сам по себе оплату не блокирует. |
| Выплаты | Заявки на вывод реферального баланса. Автоматическая выплата не имитируется сменой статуса: нужен адаптер провайдера. Ручная выплата фиксируется явно. |
| Проверка тестового контура | Staging-платёж на отдельных ключах. Боевые секреты сюда не подставляются. |
| Операции | Операционный контур сверки и диагностики. |
| Аналитика | Срезы выручки и подписок. |
| Инциденты | Открытые и закрытые инциденты. |
| Провайдеры | Включение касс, которые реально настроены в `.env`. |
| Клиенты | Список клиентов. |
| Функции | Флаги функций. |
| Ключи доступа | Хранилище passkey. Криптографическая проверка assertion в этой версии не считается включённой 2FA. |
| Карточка клиента 360 | Сводка по ID пользователя. |
| Подарки | Код, тариф, число дней и лимит использований. |
| Состояние системы | Сводный health. |
| Статус сервиса | Публичный статус, который видит и Mini App. |
| Развёртывания | История выкладок. |
| Уведомления | Шаблоны и очередь уведомлений об окончании подписки. Окно по умолчанию — `NOTIFICATION_EXPIRY_DAYS`. |

Тема панели: кнопка в шапке. Выбор человека хранится в браузере (`rw_theme`). Серверная тема по умолчанию применяется, пока локального выбора нет.

## 10. Mini App

Покупатель открывает магазин из бота. Приложение запрашивает `/api/me/dashboard`, `/api/public/config`, `/api/plans`, биллинг, центр безопасности, уведомления и публичный статус.

На экране:

- срок подписки и статус;
- список тарифов и кнопка покупки (уходит `Idempotency-Key`, выбранный провайдер и промокод);
- автопродление, если оно включено на сервере и у покупателя есть сохранённый способ YooKassa;
- отмена и возобновление подписки;
- подарочный код;
- реферальная программа и баланс;
- тикет в поддержку;
- отзыв своих сессий и выгрузка или удаление данных аккаунта.

Повторный запрос с тем же ключом идемпотентности не создаёт второе списание. Ссылка на оплату берётся из ответа провайдера. Пока `MAINTENANCE_MODE=true` или в базе включён технический режим, создание платежа отклоняется.

Если в `localStorage` нет `rw_lang`, после загрузки конфига язык берётся из `default_language`.

## 11. Бот

Команды:

- `/start` — приветствие на языке Telegram (`en`, если `language_code` начинается с `en`, иначе русский, а при пустом коде — `DEFAULT_LANGUAGE`), актуальные цены, активные акции и кнопка Mini App.
- `/promo КОД` — подсказывает открыть магазин и применить код. Сервер проверяет код ещё раз в момент оплаты.

Меню из панели (**Бот и Mini App**) заменяет кнопку по умолчанию. Пункты типа webapp и url принимаются только с `https://`. Картинка старта не должна ломать ответ: если Telegram не принял фото, бот отправляет текст.

Рассылки из панели обрабатывает цикл бота: статусы `queued` → `sending` → `completed`, аудитории all / active / inactive.

## 12. Платежи и вебхуки

Порядок один для всех касс:

1. API записывает намерение платежа.
2. Вызывает `create` провайдера через DNS-pinned HTTP-клиент (без редиректов, без переменных окружения прокси).
3. Вебхук проверяется и не считается доказательством оплаты.
4. API читает платёж у провайдера и сверяет статус успеха, сумму, валюту и `order_id`.
5. Выдача VPN идёт под блокировкой пользователя и платежа. Повтор той же операции подписку второй раз не продлевает.
6. Возврат идёт с ключом `refund-{payment_id}`. Доступ в Remnawave снимается, только если нет более новой успешно выданной оплаты. Реферальное начисление сторнируется.

YooKassa:

- Вебхук с пустым `YOOKASSA_WEBHOOK_IP_ALLOWLIST` отвечает 403 `Webhook IP not allowed`.
- IP вне списка тоже отвечает 403.
- В кабинете YooKassa укажите URL вебхука на `WEBHOOK_BASE_URL`.
- Повторное списание для автопродления использует `Idempotence-Key`, равный `order_id`.

Platega: сверяются заголовки магазина. Возврат уходит на `PLATEGA_REFUND_URL`.

RollyPay: HMAC и окно времени 5 минут. В тестовом staging-теле выставляется флаг теста. Возврат уходит на `ROLLYPAY_REFUND_URL`.

Пока production gate выключен, боевой `create` для покупателя не проводится. Сначала пройдите раздел **Проверка тестового контура**.

Рекомендуемый прогон перед включением кассы:

1. Один тестовый платёж.
2. Статус у провайдера совпал с суммой и заказом.
3. В Remnawave ровно одна выдача.
4. Повтор того же вебхука не создаёт вторую подписку.
5. Возврат отзывает доступ и появляется в финансовом журнале.

Актуальный список сетей YooKassa сверяйте с документацией провайдера перед выкладкой. Пример в `.env.example` — стартовая точка, а не вечная гарантия.

## 13. Резервные копии

Архивы пишутся в `BACKUPS_DIR` (`/data/backups` в контейнере). Расписание и срок хранения задаются в панели. Пароль шифрования хранится как настройка бэкапа.

Восстановление требует явного подтверждения. Если у администратора включена 2FA, нужен одноразовый код. Архив распаковывается только внутри своего каталога. Перед восстановлением снимается страховочная копия. Неуспешный restore оставляет технический режим, чтобы магазин не принимал оплату на повреждённых данных.

Если `BACKUP_S3_ENABLED=true`, копия уходит в S3-совместимое хранилище с префиксом `BACKUP_S3_PREFIX`. Проверьте бакет и ключи до первого ночного запуска.

## 14. Роли и сессии покупателя

Покупатель входит проверенным Telegram initData. Yandex ID включается только когда заполнены client id, secret и redirect URI. Сессия — cookie `rw_user`.

Удаление аккаунта и выдача VPN берут одну и ту же блокировку пользователя, чтобы пробный период или автопродление не создали доступ после удаления.

## 15. Что проверить после выкладки

- `docker compose ps` — backend healthy, worker и bot в состоянии running.
- Вход администратора и включённая 2FA.
- В обзоре Redis и Remnawave без ошибки.
- Создан тариф, открывается Mini App из `/start`.
- Allowlist YooKassa не пуст, если касса включена.
- Production gate выключен, пока staging-платёж не прошёл.
- Свежий бэкап виден в мониторинге.
- `METRICS_TOKEN` задан, если метрики доступны не только изнутри сети.

Чеклист короче продублирован в `PRODUCTION_CHECKLIST.md`.

## 16. Неисправности

| Симптом | Что проверить |
| --- | --- |
| Контейнер backend падает на старте | `APP_SECRET` короче 32 символов, несовпадение пароля в `DATABASE_URL` и `POSTGRES_PASSWORD`, нет прав на `MEDIA_DIR`. |
| `Webhook IP not allowed` | Пустой или неверный `YOOKASSA_WEBHOOK_IP_ALLOWLIST`, прокси не передаёт реальный IP. |
| Оплата есть, VPN нет | Статус выдачи в **Платежи**. Кнопка повтора. Доступность `REMNAWAVE_URL` и токена. Очередь в **Очередь задач** и heartbeat в **Центр восстановления**. |
| Второй вебхук продлил подписку дважды | Это дефект. В этой версии повтор той же выдачи идемпотентен. Смотрите аудит и `order_id`. |
| Платёж отклонён сразу | `MAINTENANCE_MODE`, технический режим после неудачного restore, выключенный production gate, выключенный провайдер. |
| Английский не включается | Очистите `rw_lang` и выберите EN кнопкой в шапке. Обновите страницу после смены языка. |
| Бот отвечает по-русски пользователю с английским Telegram | `language_code` должен начинаться с `en`. Иначе используется `DEFAULT_LANGUAGE`. |
| Картинки брендинга не сохраняются | Том `media_data` смонтирован в `/data/media`. Контейнер read-only пишет только туда и в `/tmp`. |
| Восстановление не стартует | Нужны роль с правом бэкапа, подтверждение и TOTP, если 2FA включена. |

Журналы: `docker compose logs backend worker bot --tail 200`.

---

# Full instruction — Remnawave VPN Shop 2.2.1

This is the operator guide for installing the shop, turning payments on, and running the admin panel. A function-by-function code reference is in `FUNCTIONS.md`. The security model is in `SECURITY.md`.

## 1. What it is

A VPN shop: Telegram bot, Mini App, admin console, and API. A buyer picks a plan and pays through YooKassa, Platega, or RollyPay. After the provider confirms the payment, the API creates or extends a Remnawave user. A worker drains fulfillment, reconciliation, and notification jobs.

Compose services: `db` (PostgreSQL 16), `redis`, `backend` (FastAPI), `worker`, `bot`, `admin`, `miniapp`, `caddy`. PostgreSQL and Redis are not published on the host. Caddy publishes TCP 80, TCP 443, and UDP 443.

The admin UI, Mini App, and bot replies are available in Russian and English.

## 2. Requirements

- Debian or Ubuntu with root for `install.sh`, or any host with Docker Engine and the Compose plugin.
- A domain pointing at the server when Caddy should issue HTTPS. `localhost` is enough for a local check.
- A Remnawave panel URL and API token.
- A BotFather token and a public HTTPS Mini App URL.
- For live payments: credentials for the chosen provider and, for YooKassa, a webhook IP allowlist.

`APP_SECRET` must be at least 32 characters. The sample admin password is at least 12 characters. The sample database password uses only letters and digits so `DB_PASSWORD`, `POSTGRES_PASSWORD`, and `DATABASE_URL` stay identical.

## 3. One-command install

On a clean Debian or Ubuntu host:

```bash
sudo bash install.sh
```

The script installs Docker, asks for values it cannot invent, generates `APP_SECRET` and the database password, writes `.env` as mode `0600`, builds images, starts PostgreSQL and Redis, runs Alembic migrations, and prints the admin, Mini App, and API URLs. It configures UFW (SSH, TCP 80/443, UDP 443) and Fail2Ban for SSH.

`install.sh` is a standalone installer. It does not call a separate `deploy/install-vps.sh`. The `deploy/` directory holds the Caddyfile and helper files.

The project directory is usually `/opt/vpn-shop`. Checks:

```bash
cd /opt/vpn-shop
./scripts/preflight.sh
./scripts/security-scan.sh
./scripts/doctor.sh
```

Update and rollback:

```bash
./scripts/update.sh
./scripts/rollback.sh
```

2FA stays off until an administrator enables it under **Security**.

## 4. Docker Compose install

```bash
cp .env.example .env
```

Fill `APP_SECRET`, `DB_PASSWORD` (the same value in `POSTGRES_PASSWORD` and `DATABASE_URL`), `BOT_TOKEN`, `BOT_USERNAME`, `REMNAWAVE_URL`, `REMNAWAVE_TOKEN`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, the domains `API_DOMAIN`, `ADMIN_DOMAIN`, `APP_DOMAIN`, and the public URLs `PUBLIC_BASE_URL` and `MINI_APP_URL`. For YooKassa also set `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, and a non-empty `YOOKASSA_WEBHOOK_IP_ALLOWLIST`.

```bash
docker compose up -d --build
docker compose ps
```

Compose sets `MEDIA_DIR=/data/media`, `BACKUPS_DIR=/data/backups`, and `PROJECT_DIR=/project` on the backend and worker. Those values override `.env`. Volumes: `media_data`, `backup_data`, and a read-only mount of the project at `/project`. Backend and worker use a read-only root filesystem and a tmpfs on `/tmp`.

API liveness inside the compose network is `GET /health` on port 8000 of `backend`.

## 5. Running without containers

You need Python 3.12, Node.js, PostgreSQL, and Redis. Point `MEDIA_DIR` at a writable directory. The defaults `/data/media`, `/data/backups`, and `/project` match the containers. On a workstation use something like `MEDIA_DIR=./data/media`.

```bash
cd backend
alembic upgrade head
cd ../admin && npm ci && npx vite build
cd ../miniapp && npm install && npx vite build
python3 -m compileall -q backend
python3 -m pytest -q
```

The tests under `tests/` mostly lock source contracts. They do not call live payment providers or Remnawave.

## 6. Settings that change this release

The annotated list is `.env.example`.

| Variable | Role |
| --- | --- |
| `APP_SECRET` | JWT signing and encryption of TOTP, recovery codes, and the staging config. At least 32 characters. |
| `APP_SECRET_PREVIOUS` | Only during a key rotation. Clear it afterwards. |
| `APP_ENV` | `production` or `development`. |
| `DEFAULT_LANGUAGE` | `ru` or `en`. Bot language and the Mini App starting language until a person chooses. |
| `MAINTENANCE_MODE` | `true` rejects payment creation in-process, before the database flag is read. |
| `BOT_TOKEN`, `BOT_USERNAME` | Telegram bot. |
| `ADMIN_TELEGRAM_ID` | Administrator Telegram id used for alerts and Telegram admin sign-in where that path applies. |
| `REMNAWAVE_URL`, `REMNAWAVE_TOKEN` | Remnawave panel. |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | First administrator. |
| `ADMIN_CORS_ORIGINS` | Comma-separated origins. |
| `COOKIE_SECURE`, `COOKIE_SAMESITE` | For HTTPS and Telegram WebApp, typically `true` and `none`. |
| `YOOKASSA_WEBHOOK_IP_ALLOWLIST` | Required for YooKassa webhooks. An empty list rejects the webhook. |
| `PLATEGA_*`, `ROLLYPAY_*` | Secrets and refund URLs for those providers. |
| `AUTO_RENEW_ENABLED` | YooKassa saved-method renewal. Off by default. |
| `BACKUP_S3_*`, `S3_*` | Off-site backup copy. Object prefix is `BACKUP_S3_PREFIX` (`vpn-shop`). |
| `METRICS_TOKEN` | Protects `/metrics`. |
| `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET`, `YANDEX_REDIRECT_URI` | All three are required to enable Yandex ID. Empty values leave it off. |
| `MEDIA_DIR`, `BACKUPS_DIR`, `PROJECT_DIR` | Media, backup archives, and the source mount. Compose sets them on the service. |

Live charges stay closed until an administrator passes staging end-to-end checks and enables the production payment gate. The staging call uses only the credentials sent with that request.

## 7. First administrator sign-in

1. Open the admin host (`ADMIN_DOMAIN`, or the URL printed by the installer).
2. Enter `ADMIN_EMAIL` and `ADMIN_PASSWORD`. Leave TOTP empty until 2FA is on.
3. Open **Security**, start 2FA setup, store the recovery codes, and confirm a code from the authenticator app.
4. Under **Plans**, create at least one enabled plan: name, price, duration in days.
5. Under **Bot and Mini App**, check the bot name, the Mini App URL (`https://`), and the menu.
6. Under **Providers**, enable only the cashiers whose keys are in `.env`.
7. Run a test payment under **Staging checks**, then allow real payments.
8. Under **Backups**, set a schedule and an encryption password and run the first copy.

The admin session is the HttpOnly cookie `rw_admin`. It is bound to the user agent, expires after 15 idle minutes, and never outlives the token. Mutations send `X-CSRF-Token` equal to the `rw_csrf` cookie. **End all** under **Sessions** revokes every session of the current administrator.

Telegram sign-in on the login form works when the panel is opened inside a Telegram WebApp and initData verifies.

## 8. Interface language

The language button in the admin and Mini App headers switches `RU` and `EN`. The choice is stored in `localStorage` under `rw_lang`. Until that key exists:

- the admin UI follows the browser language;
- the Mini App, after `/api/public/config`, uses the server `default_language` (`DEFAULT_LANGUAGE`) when no saved choice exists;
- the bot uses the Telegram `language_code`, otherwise `DEFAULT_LANGUAGE`.

Russian strings stay in the UI source. English is applied after render by `admin/src/i18n.tsx` and `miniapp/src/i18n.tsx`. `prompt` and `confirm` dialogs use the same dictionary. Plan names, database rows, and broadcast texts are not translated by the interface language.

## 9. Admin sections

Roles are `viewer`, `operator`, and `admin`. A missing permission returns HTTP 403. A viewer can read users, payments, marketing, analytics, and support, and can manage their own 2FA. An operator manages plans, users, payments except refunds, content, broadcasts, support, diagnostics, incidents, providers, and feature flags. An administrator also manages other administrators, backups, refunds, reconciliation, staging, sessions, and referral payouts.

| Section | What it is for |
| --- | --- |
| Panel branding | Name, logo, favicon, default theme. Uploads are re-encoded. The previous file is deleted by basename inside `MEDIA_DIR`. |
| Overview | Users, active VPNs, revenue, fulfillment errors, API, Redis, and Remnawave health. |
| Enterprise suite | Monitoring checks, campaigns, rules, device summary. New rules are created disabled. |
| Sessions | Administrator sessions; end one session or all of your own. |
| Plans | Create and delete plans. Price and duration feed the Mini App catalog. |
| Payments | Intents, payment and fulfillment status, retry, reconciliation. |
| Financial ledger | Revenue, refunds, and referral entries. |
| Users | Buyer and subscription records. |
| Bot and Mini App | Bot name, start image, menu items, fields, announcements. Menu links must be `https://`. |
| Marketing | Promotions and promo codes, windows, and plan scope. |
| Administrators | Accounts with role `viewer`, `operator`, or `admin`. |
| Backups | Schedule of 6/12/24 hours or off, retention, password, run, verify, restore. |
| Security | 2FA, recovery codes, production-gate indicator. |
| Recovery center | Worker heartbeat, stuck jobs, recovery actions. |
| Audit | Administrator action log. |
| Support | Buyer tickets. |
| Refunds | Provider refund and VPN revoke when no newer fulfilled payment still entitles the buyer. |
| Workers | Worker fleet status. |
| Releases | Update channel and rollback. Check the manifest signature when `RELEASE_MANIFEST_PUBLIC_KEY` is set. |
| Monitoring | API metrics, disk, backup freshness, fulfillment failures. |
| Job queue | `queued`, `processing`, `completed`, `failed`, attempts, and lease. |
| Anti-fraud | Velocity signals. One weak signal does not block a payment by itself. |
| Payouts | Referral withdrawal requests. Changing a status does not send money. A manual payout is recorded explicitly. An automatic payout needs a provider adapter. |
| Staging checks | A staging payment with separate keys. Production secrets are not read here. |
| Operations | Reconciliation and diagnostics. |
| Analytics | Revenue and subscription slices. |
| Incidents | Open and closed incidents. |
| Providers | Enable cashiers that are actually configured in `.env`. |
| Customers | Customer list. |
| Features | Feature flags. |
| Passkeys | Stored passkey material. Cryptographic assertion checks are not treated as enabled 2FA in this version. |
| Customer 360 | Summary by user id. |
| Gifts | Code, plan, days, and redemption limit. |
| System health | Combined health. |
| Service status | Public status also shown in the Mini App. |
| Deployments | Release history. |
| Notifications | Templates and the expiry notice queue. The default window is `NOTIFICATION_EXPIRY_DAYS`. |

The header theme button stores `rw_theme` in the browser. The server default applies until a local choice exists.

## 10. Mini App

The buyer opens the shop from the bot. The app loads `/api/me/dashboard`, `/api/public/config`, `/api/plans`, billing, the security center, notifications, and the public status.

The screen shows the subscription expiry and status, the plan list and a buy action (with `Idempotency-Key`, the selected provider, and an optional promo code), auto-renew when the server flag is on and a YooKassa method is saved, cancel and resume, gift redemption, the referral program and balance, a support ticket, session revoke, and account export or deletion.

The same idempotency key does not create a second charge. The payment URL comes from the provider response. `MAINTENANCE_MODE=true` or the database maintenance flag rejects new payments.

When `rw_lang` is absent, the language follows `default_language` after config loads.

## 11. Bot

- `/start` greets the user in the Telegram language (`en` when `language_code` starts with `en`, otherwise Russian, and `DEFAULT_LANGUAGE` when the code is empty), lists current prices and active promotions, and shows the Mini App button.
- `/promo CODE` tells the user to open the shop and apply the code. The server validates the code again at payment time.

A menu saved under **Bot and Mini App** replaces the default button. WebApp and URL items must use `https://`. If Telegram rejects the start image, the bot still sends the text.

Broadcasts move `queued` → `sending` → `completed` for audiences all, active, and inactive.

## 12. Payments and webhooks

1. The API stores a payment intent.
2. It calls the provider `create` method through the DNS-pinned HTTP client (redirects off, proxy environment ignored).
3. The webhook is checked and is not proof of payment.
4. The API re-reads the payment and checks success, amount, currency, and `order_id`.
5. VPN fulfillment takes a user lock and a payment lock. Repeating the same operation does not extend the subscription twice.
6. Refunds use the key `refund-{payment_id}`. Remnawave access is revoked only when no newer fulfilled payment still entitles the buyer. The referral reward is reversed.

YooKassa:

- An empty `YOOKASSA_WEBHOOK_IP_ALLOWLIST` returns 403 `Webhook IP not allowed`.
- An IP outside the list also returns 403.
- Point the YooKassa webhook at `WEBHOOK_BASE_URL`.
- Recurring charges use an `Idempotence-Key` equal to `order_id`.

Platega compares the merchant headers. Refunds go to `PLATEGA_REFUND_URL`.

RollyPay checks HMAC and a five-minute timestamp window. Staging payloads set the test flag. Refunds go to `ROLLYPAY_REFUND_URL`.

While the production gate is off, a buyer cannot start a live charge. Use **Staging checks** first.

Before enabling a cashier:

1. Run one test payment.
2. Confirm the provider status matches the amount and the order.
3. Confirm exactly one Remnawave fulfillment.
4. Replay the webhook and confirm the subscription is not extended again.
5. Refund, confirm access is revoked, and confirm the ledger entry.

Recheck YooKassa’s published network list before go-live. The sample in `.env.example` is a starting point.

## 13. Backups

Archives are written to `BACKUPS_DIR` (`/data/backups` in the container). Schedule and retention are set in the panel.

Restore requires an explicit confirmation. If the administrator has 2FA, a one-time code is required. The archive is extracted only inside its own directory. A safety copy is taken first. A failed restore leaves maintenance mode on so the shop does not take payments against damaged data.

With `BACKUP_S3_ENABLED=true`, a copy is uploaded to S3-compatible storage under `BACKUP_S3_PREFIX`. Check the bucket and keys before the first scheduled run.

## 14. Buyer roles and sessions

Buyers sign in with verified Telegram initData. Yandex ID turns on only when the client id, secret, and redirect URI are all set. The session cookie is `rw_user`.

Account deletion and VPN fulfillment share the user lock so a trial or auto-renew cannot create access after deletion.

## 15. After deploy

- `docker compose ps` shows a healthy backend and running worker and bot.
- Administrator sign-in works and 2FA is on.
- Overview shows Redis and Remnawave without an error.
- A plan exists and `/start` opens the Mini App.
- The YooKassa allowlist is non-empty when that cashier is enabled.
- The production gate stays off until the staging payment succeeds.
- Monitoring shows a fresh backup.
- `METRICS_TOKEN` is set if metrics are reachable outside the private network.

A shorter list is in `PRODUCTION_CHECKLIST.md`.

## 16. Troubleshooting

| Symptom | Check |
| --- | --- |
| Backend container exits on start | `APP_SECRET` shorter than 32 characters, password mismatch between `DATABASE_URL` and `POSTGRES_PASSWORD`, or no write access to `MEDIA_DIR`. |
| `Webhook IP not allowed` | Empty or wrong `YOOKASSA_WEBHOOK_IP_ALLOWLIST`, or the proxy is not forwarding the client IP. |
| Paid, but no VPN | Fulfillment status under **Payments**, the retry action, `REMNAWAVE_URL` and token, the job queue, and the worker heartbeat in **Recovery center**. |
| A second webhook extended the subscription twice | That is a defect. Repeating the same fulfillment is idempotent in this version. Inspect the audit log and `order_id`. |
| Payment rejected immediately | `MAINTENANCE_MODE`, maintenance after a failed restore, production gate off, or the provider disabled. |
| English does not switch | Clear `rw_lang`, press EN in the header, and reload. |
| The bot answers in Russian to an English Telegram client | `language_code` must start with `en`. Otherwise the bot uses `DEFAULT_LANGUAGE`. |
| Branding images do not save | The `media_data` volume is mounted at `/data/media`. The read-only container writes only there and to `/tmp`. |
| Restore does not start | The role needs backup permission, plus confirmation and TOTP when 2FA is enabled. |

Logs: `docker compose logs backend worker bot --tail 200`.
