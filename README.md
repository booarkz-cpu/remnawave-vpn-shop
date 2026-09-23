# Remnawave VPN Shop 3.1.4

Платформа магазина VPN: Telegram-бот, Mini App, отдельный личный кабинет, админ-панель Material Design + Web 3.0, отдельные приложения Android и iOS для покупателя и администратора, API, платежи YooKassa / Platega / RollyPay и sandbox без шлюзов, конструктор тарифа, статус узлов Remnawave, антиабьюз, агент узла, выдача доступа, очереди и резервные копии.

Состояние: **3.1.4**. Предыдущие релизы: **3.1.3**, **3.1.2**, **3.1.1**, **3.1.0**, **3.0.1**, **3.0.0-realise**, **2.13.0**, **2.12.0**, **2.11.0**, **2.10.0**, **2.9.0**, **2.8.0**, **2.7.0**, **2.6.0**, **2.5.0** и **2.4.0**. Перед production пройдите `INSTALL_STEPS.md`, `INSTRUCTION.md` (разделы 9.18, 9.17, 9.16 и 9.15), `MOBILE.md`, `MODULES.md`, `SECURITY.md` и `PRODUCTION_CHECKLIST.md`. Лицензия — `LICENSE`.

## Русский

### Состав

| Часть | Технология | Зачем |
| --- | --- | --- |
| API и бот | Python, FastAPI, aiogram, PostgreSQL, Redis | Магазин, платежи, выдача VPN, фоновые задачи |
| Админка | React, Vite | Тарифы, конструктор, узлы, платформа, платежи и кабинет |
| Mini App | React, Vite, Telegram WebApp | Покупка внутри Telegram |
| Личный кабинет | React, Vite | Вход по email, Telegram, VK и Яндексу |
| Android и iOS | Kotlin Compose, SwiftUI | Покупатель и администратор, русский и английский |
| Периметр | Docker Compose, Caddy | HTTPS и разделение доменов |
| Проверки | `tests/`, `scripts/sandbox-e2e.sh` | Регрессия и прогон без живых касс |

### Возможности 3.1.4

- **Первый запуск больше не роняет API.** Backend и worker больше не создают `alembic_version` одновременно. Если контейнер всё же не поднялся, установщик печатает логи backend и worker, а не только `installation failed at line 382`.
- Пробелы в ответах снимаются. Часовой пояс `Moscow` записывается как `Europe/Moscow`.
- Схема остаётся `0038_v2_6_0_platform`. Покупатель Android остаётся **2.10.0**, администратор — **2.12.0**. Подробности — раздел 9.18 `INSTRUCTION.md` и `RELEASE_NOTES_V3_1_4.md`.

### Возможности 3.1.3

- **Установка через `curl | bash` дожидается ответов.** Канал занят скриптом, поэтому вопросы читаются с терминала SSH. В 3.1.2 первый вопрос завершался `installation failed at line 34`.
- Схема остаётся `0038_v2_6_0_platform`. Покупатель Android остаётся **2.10.0**, администратор — **2.12.0**. Подробности — раздел 9.17 `INSTRUCTION.md` и `RELEASE_NOTES_V3_1_3.md`.

### Возможности 3.1.2

- **Ключи VPN не видны роли viewer.** Подписка и ключи Remnawave требуют право `users.keys`. Списки и карточка пользователя отдают поля без ссылки подписки и паролей. Обзор показывает только общее число пользователей.
- **Ответы панели без текста исключения.** Диагностика, задания, копии, провайдеры, выплаты, мониторы, журнал аудита и причины возвратов не возвращают stderr и строки исключений. Подробность остаётся в журнале процесса.
- **UUID пользователя Remnawave.** Карточка, продление, подписка и ключи принимают строковый идентификатор.
- Схема остаётся `0038_v2_6_0_platform`. Покупатель Android остаётся **2.10.0**, администратор — **2.12.0**. Подробности — раздел 9.16 `INSTRUCTION.md` и `RELEASE_NOTES_V3_1_2.md`.

### Возможности 3.1.1

- **Секреты staging сохраняются.** Повторное сохранение вкладки **Проверка тестового контура** оставляет пустое поле секрета, Shop ID и Merchant ID как уже записанное значение. Совпадение с ключами из `.env` по-прежнему отклоняется.
- **Адрес оплаты в журнале.** Раннер печатает `[CHECKOUT]` и https-ссылку. Статус `awaiting_checkout` production gate не открывает. Кнопка **Разрешить реальные платежи** ждёт `FULL_E2E_PASS` моложе 24 часов. Порядок — раздел 9.15 `INSTRUCTION.md`.
- **Журнал без секретов.** Перед записью статуса токены и секреты длиннее 7 символов заменяются на `[скрыто]`.
- **Установка по шагам.** `INSTALL_STEPS.md` перечисляет каждый вопрос `install.sh` и `deploy/install-vps.sh`.
- Схема остаётся `0038_v2_6_0_platform`. Покупатель Android остаётся **2.10.0**, администратор — **2.12.0**. Подробности — `RELEASE_NOTES_V3_1_1.md`.

### Возможности 3.1.0

- **Публичный список тарифов** больше не отдаёт `remnawave_profile_id`. Идентификатор профиля остаётся в панели администратора и в снимке платежа.
- **Статус автопродления** для покупателя при ошибке отвечает фразой «Автопродление не выполнено». Текст исключения остаётся в базе и в журнале.
- **Контрольная сумма пакета.** Загрузка APK или IPA считает SHA-256. Кабинет и панель показывают её только вместе со ссылкой на скачивание. Имя файла на диске по-прежнему скрыто.
- **Файл подписки.** `GET /api/me/subscription-file` отдаёт ссылку подписки текстовым файлом `remnawave-subscription.txt`. В кабинете, вкладка «Подключение», кнопка **Скачать подписку**.
- **Справка по установке.** `GET /api/public/apps/install` возвращает карточки магазина, официальные ссылки GitHub и шаги на русском и английском.
- Схема остаётся `0038_v2_6_0_platform`. Покупатель Android остаётся **2.10.0**, администратор — **2.12.0**. Подробности — раздел 9.14 в `INSTRUCTION.md` и `RELEASE_NOTES_V3_1_0.md`.

### Как скачать приложения для Android и iOS

Пакеты проекта и файл, который загрузил администратор вашего магазина, — разные ссылки. Кабинет отдаёт загруженный файл. Ссылки ниже — сборки этого репозитория.

**Android, покупатель 2.10.0**

1. Скачайте APK: https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.10.0/remnawave_vpn_shop_android_user_2_10_0.apk
2. Скачайте контрольную сумму: https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.10.0/remnawave_vpn_shop_android_user_2_10_0.apk.sha256
3. В каталоге, где лежат оба файла, выполните `sha256sum -c remnawave_vpn_shop_android_user_2_10_0.apk.sha256`.
4. На телефоне разрешите установку из выбранного источника и откройте APK.
5. Если администратор магазина загрузил свой APK, в личном кабинете кнопка **Скачать** на карточке Android ведёт на `GET /api/public/apps/android-user/download`. Рядом показана контрольная сумма этого файла.

**Android, администратор 2.12.0**

1. Скачайте APK: https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.12.0/remnawave_vpn_shop_android_admin_2_12_0.apk
2. Скачайте контрольную сумму: https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.12.0/remnawave_vpn_shop_android_admin_2_12_0.apk.sha256
3. В том же каталоге выполните `sha256sum -c remnawave_vpn_shop_android_admin_2_12_0.apk.sha256`.
4. В панели, вкладка **Приложения**, блок **Скачать приложение администратора** отдаёт файл, загруженный администратором: `GET /api/admin/apps/android-admin/download`. Нужна сессия с правом `read`.

**iOS**

Готового IPA в релизах GitHub нет. Администратор магазина может загрузить подписанный IPA. Тогда кабинет покупателя открывает `GET /api/public/apps/ios-user/download`, а панель — `GET /api/admin/apps/ios-admin/download`. Собрать и подписать пакет можно в Xcode на macOS из каталогов `mobile/ios-user` и `mobile/ios-admin`.

Краткая справка без входа: `GET /api/public/apps/install`.

### Возможности 3.0.1

- **Автопродление и шифрованная копия.** Секрет расшифровывается через `decrypt_secret` из пакета `app`. В контейнере больше нет импорта `backend.app.security`, из‑за которого продление и проверка копии отвечали ошибкой.
- **Баланс списывается один раз.** `POST /api/me/wallet/spend` требует `Idempotency-Key`. Повтор с тем же ключом возвращает уже созданный платёж. Другой ключ на ту же покупку в течение 30 секунд получает 409 и не списывает баланс второй раз. Покупка подарка повторно проверяет ключ уже под блокировкой пользователя.
- **Второй счёт на ту же покупку.** Новый `Idempotency-Key` в течение 30 секунд не открывает второй сеанс провайдера, пока предыдущий счёт на тот же снимок тарифа ещё создаётся или ожидает оплаты.
- Схема остаётся `0038_v2_6_0_platform`. Покупатель Android остаётся **2.10.0**, администратор — **2.12.0**. Подробности — раздел 9.13 в `INSTRUCTION.md`, `SECURITY.md` и `RELEASE_NOTES_V3_0_1.md`.

### Возможности 3.0.0-realise

- **Пакет приложения до 80 МБ.** `POST /api/admin/apps/{id}/file` больше не упирается в общий потолок тела 12 МБ, если у запроса есть `Content-Length`. Запрос без `Content-Length` по-прежнему ограничен 12 МБ. Право `manage_content` проверяется до чтения файла.
- **Секреты не уходят в прокси окружения.** Вызовы Telegram, Яндекс OAuth и Remnawave создают HTTP-клиент с `trust_env=False`.
- **Адрес клиента.** Заголовок `X-Forwarded-For` учитывается только если непосредственный сосед — loopback, частный или link-local адрес (Caddy). Прямой клиент не может подставить адрес из allowlist вебхука.
- **Ответы без текста исключения.** Повтор выдачи и сводка здоровья не возвращают строку исключения. Подробность остаётся в журнале процесса.
- Схема базы остаётся `0038_v2_6_0_platform`. Приложения Android покупателя остаются **2.10.0**, администратора — **2.12.0**. Подробности — раздел 9.12 в `INSTRUCTION.md` и `RELEASE_NOTES_V3_0_0.md`.

### Возможности 2.13.0

- **Скачивание приложений.** Панель, вкладка «Приложения», даёт ссылку на приложение администратора. Личный кабинет даёт ссылку на приложение покупателя. Администратор загружает APK или IPA и меняет тексты, видимость и https-ссылку карточки. Подробности — раздел 9.11 в `INSTRUCTION.md` и `RELEASE_NOTES_V2_13_0.md`.
- Схема базы остаётся `0038_v2_6_0_platform`. Приложения Android покупателя остаются **2.10.0**, администратора — **2.12.0**.

### Возможности 2.12.0

- **Массовая рассылка в Telegram.** Веб-панель, раздел «Маркетинг», и приложения администратора Android и iOS ставят сообщение в очередь `POST /api/admin/broadcasts`. Доставляет процесс бота. Аудитория: все с Telegram, активная подписка или без активной подписки. Кнопка и картинка — только `https://`. Повтор `POST /api/admin/broadcasts/{id}/retry` продолжает с сохранённого счётчика. Подробный разбор — `RELEASE_NOTES_V2_12_0.md` и раздел 9.10 в `INSTRUCTION.md`.
- Приложение администратора Android: `versionName` **2.12.0**, `versionCode` **2120**. iOS-администратор: `MARKETING_VERSION` **2.12.0**. Приложение покупателя остаётся **2.10.0**. Схема базы остаётся `0038_v2_6_0_platform`.

### Возможности 2.11.0

- **README и инструкции на двух языках.** Этот файл и `INSTRUCTION.md`, `INSTALL.md`, `MODULES.md`, `SECURITY.md`, `MOBILE.md` читаются по-русски и по-английски.
- **Обновление всего проекта с GitHub.** Команда на сервере: `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`. Скрипт скачивает zip `full_release` и файл `.sha256` только с GitHub, отклоняет чужой хост, symlink, путь с `..` и архив больше 80 МБ. `.env` не затирается. `scripts/update.sh` сначала снимает снимок текущей установки и делает `pg_dump`, и только потом копирует новые файлы. Ошибка сборки откатывает этот снимок. API архив не распаковывает. Вкладка «Релизы» показывает статус через `GET /api/admin/github-update`. Cron не включён.
- Схема базы остаётся `0038_v2_6_0_platform`. Лицензия прежняя, файл `LICENSE`. APK покупателя и администратора остаются пакетами **2.10.0** из того релиза.

### Возможности 2.10.0

- **Release APK.** `remnawave_vpn_shop_android_user_2_10_0.apk` и `remnawave_vpn_shop_android_admin_2_10_0.apk`, `versionCode` 2100. Сертификат и контрольные суммы — в `RELEASE_NOTES_V2_10_0.md`. Пакеты 2.9.0 были debug-подписаны, перед 2.10.0 их удаляют один раз. Закрытый ключ в релиз не входит.
- **Один шаг подключения.** QR `GET /api/me/connection-qr` и кнопки Happ, v2rayNG, Streisand для `https://` ссылки подписки.
- **Устройства, трафик, подарок и пополнение.** Список устройств без `device_key` и `last_ip`. Трафик с запасным лимитом из снимка. Подарок и пополнение кошелька, включая sandbox при `PAYMENTS_SANDBOX=true`.
- **Подпись клиента и биометрия.** HMAC `X-Shop-Proof`. Сохранённый токен закрывается биометрией или PIN. `MOBILE_REQUIRE_PROOF=false` оставляет рабочими приложения 2.9.0.
- **Telegram.** Срок подписки, пополнение и успешная оплата. Ошибка отправки не откатывает платёж.
- **Дежурство в приложении администратора.** Включение тарифа, карточка платежа без текста ошибки провайдера, признак устаревшего агента.
- **iOS.** Исходники с `MARKETING_VERSION` 2.10.0. IPA собирается в Xcode на macOS. В релизе IPA нет.

### Возможности 2.9.0

- **APK для Android.** Релиз GitHub содержит два debug-подписанных пакета для ручной установки: покупатель `remnawave_vpn_shop_android_user_2_9_0.apk` и администратор `remnawave_vpn_shop_android_admin_2_9_0.apk`. Повторная сборка — `scripts/build-android-apk.sh`.
- **iOS.** Исходники `mobile/ios-user` и `mobile/ios-admin` открываются в Xcode на macOS. IPA собирается там же. В архиве этого релиза IPA нет.
- Платёжная ссылка в приложении покупателя открывается после разбора адреса: `https`, либо `http` только для `localhost`, `127.0.0.1` и `10.0.2.2`.
- User-Agent приложений: `RemnawaveShop-Android-User/2.9.0`, `RemnawaveShop-Android-Admin/2.9.0`, `RemnawaveShop-iOS-User/2.9.0`, `RemnawaveShop-iOS-Admin/2.9.0`.

### Возможности 2.8.0

- **Каталог приложений.** Вкладка админки «Приложения»: тексты на русском и английском, ссылка и видимость для Android и iOS покупателя и администратора.
- **Логотип кабинета и приложений.** Загрузка PNG/JPG/WEBP. Кабинет покупателя и четыре приложения показывают один и тот же файл. Логотип самой панели задаётся отдельно в «Брендинг панели».
- Публичный ответ `GET /api/public/apps` содержит только включённые карточки покупателя.

### Возможности 2.7.0

- **Четыре приложения.** `mobile/android-user`, `mobile/android-admin`, `mobile/ios-user`, `mobile/ios-admin`. Покупатель покупает тариф, собирает конструктор, видит серверы и копирует ссылку подписки. Администратор смотрит обзор, платежи, мониторинг и разбирает нарушения.
- **Язык в приложении.** Переключатель RU/EN. Каталоги `mobile/l10n/user.json` и `mobile/l10n/admin.json`.
- **Сессия.** Заголовок `X-Shop-Client` получает `access_token` в JSON. Веб-вход остаётся на HttpOnly cookie и токен в JSON не кладёт.
- **Лицензия приложений.** Тот же файл `LICENSE`, Remnawave VPN Shop Proprietary License 1.0. Разбор функций — `MOBILE.md`.

### Возможности 2.6.0

- **Платформа.** Вкладка «Платформа»: скоринг разделения подписки, агенты узлов, чёрный список HWID, ключи API, исходящие webhook, счётчики стран. Секрет показывается один раз.
- **Агент узла.** `scripts/node-agent.py` отправляет heartbeat и наблюдения. Действия на узле — только `throttle` и `clear`, и только если на узле задан `AGENT_APPLY_TC=1`.
- **Почта и метрики.** Тестовое SMTP-письмо уходит администратору, который нажал кнопку. DKIM выдаёт TXT-запись. `/metrics` добавляет три ряда, дашборд лежит в `deploy/grafana/vpnshop-platform.json`.
- **Кабинет на домашний экран.** `cabinet/public/manifest.webmanifest`.
- **Семь тем админки:** dark, light, midnight, graphite, lagoon, amber, paper.
- **Лицензия.** Remnawave VPN Shop Proprietary License 1.0, файл `LICENSE`, русский и английский текст.

### Возможности 2.5.0

- **Конструктор тарифов.** Администратор задаёт базовую цену и пункты: число устройств, объём трафика (0 = безлимит) и срок в днях. Покупатель собирает комбинацию в кабинете и в Mini App. Цена = база + выбранные пункты. Снимок срока, трафика и устройств записывается в платёж и не меняется, если конструктор потом отредактируют.
- **Мониторинг Remnawave.** В админке вкладка «Мониторинг Remnawave» показывает доступность панели, задержку и статус узлов. Покупатель видит отдельный раздел «Серверы» и краткий статус на обзоре. Публичный и пользовательский ответы не содержат адресов, токенов и сырого JSON панели.
- **Проверка до релиза без касс.** `PAYMENTS_SANDBOX=true` и `bash scripts/sandbox-e2e.sh`. Живые YooKassa, Platega и RollyPay для этого прогона не нужны.
- Интерфейсы и документы GitHub на **русском и английском**.

Уже было в 2.4.0 и сохранено: личный кабинет, CMS вкладок, инструкции Android / iOS / TV / компьютер, кошелёк, подарки, пробный период, промокоды, рефералы, автопродление, RBAC, 2FA, бэкапы.

### Быстрый старт

```bash
cp .env.example .env
# Заполните APP_SECRET, пароль БД, BOT_TOKEN, REMNAWAVE_*, ADMIN_*,
# API_DOMAIN, ADMIN_DOMAIN, APP_DOMAIN, CABINET_DOMAIN.
# Для проверки без касс: PAYMENTS_SANDBOX=true
docker compose up -d --build
bash scripts/sandbox-e2e.sh
```

Одношаговая установка на Debian/Ubuntu:

```bash
sudo bash install.sh
```

Обновление уже установленного магазина с GitHub:

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

Подробности — в `INSTRUCTION.md`, раздел 9.9. Не коммитьте `.env`, токены и пароли.

### Документация

| Файл | Содержание |
| --- | --- |
| `INSTRUCTION.md` | Полная инструкция RU/EN, включая тест без касс и обновление с GitHub |
| `MODULES.md` | Каждый модуль и зачем он нужен, RU/EN |
| `FUNCTIONS.md` | Разбор функций кода, RU/EN |
| `SECURITY.md` | Модель безопасности RU/EN |
| `DOCUMENTATION.md` | Карта актуальных документов и архивных аудитов |
| `LICENSE` | Проприетарная лицензия 1.0, RU/EN |
| `MOBILE.md` | Android и iOS: функции, сессия, логотип, сборка, RU/EN |
| `RELEASE_NOTES_V3_1_0.md` | Аудит 3.1.0, контрольная сумма и скачивание приложений |
| `RELEASE_NOTES_V3_0_1.md` | Аудит 3.0.1: автопродление, копия и баланс |
| `RELEASE_NOTES_V3_0_0.md` | Аудит 3.0.0-realise и результат чеклиста |
| `RELEASE_NOTES_V2_13_0.md` | Скачивание приложений 2.13.0 |
| `RELEASE_NOTES_V2_12_0.md` | Рассылка 2.12.0, разбор функций и проверка |
| `RELEASE_NOTES_V2_11_0.md` | Документация 2.11.0 и безопасный порядок обновления |
| `RELEASE_NOTES_V2_10_0.md` | Что вошло в 2.10.0, release APK, подпись клиента |
| `RELEASE_NOTES_V2_9_0.md` | Что вошло в 2.9.0, APK и сборка iOS |
| `RELEASE_NOTES_V2_8_0.md` | Что вошло в 2.8.0 |
| `RELEASE_NOTES_V2_7_0.md` | Что вошло в 2.7.0 |
| `RELEASE_NOTES_V2_6_0.md` | Что вошло в 2.6.0 и границы реализации |
| `RELEASE_NOTES_V2_5_0.md` | Что вошло в 2.5.0 и чего нет из внешних проектов |
| `INSTALL.md` | Установщик, RU/EN |
| `PRODUCTION_CHECKLIST.md` | Чеклист production |
| `.env.example` | Переменные окружения |

### Локальная проверка

```bash
python3 -m compileall -q backend
python3 -m pytest -q
bash -n install.sh deploy/install-vps.sh scripts/sandbox-e2e.sh scripts/update.sh scripts/update-from-github.sh
cd admin && npm ci && npx vite build
cd ../miniapp && npm install && npx vite build
cd ../cabinet && npm install && npx vite build
```

### Лицензия

**Remnawave VPN Shop Proprietary License 1.0** (`SPDX-License-Identifier: LicenseRef-Proprietary`). Полный текст на русском и английском — в `LICENSE`.

Чтение репозитория разрешено. Копирование, изменение, распространение и запуск как услуги для третьих лиц требуют письменного разрешения владельца репозитория booarkz-cpu/remnawave-vpn-shop. Программа поставляется «как есть», без гарантий.

## English

A VPN shop with a Telegram bot, a Mini App, a standalone user cabinet, an admin console, separate Android and iOS apps for buyers and administrators, a FastAPI backend, three payment providers plus a sandbox provider, a tariff constructor, Remnawave node status, abuse scoring, a node agent, provisioning, queues and backups.

Current release: **3.1.4**. Previous releases: **3.1.3**, **3.1.2**, **3.1.1**, **3.1.0**, **3.0.1**, **3.0.0-realise**, **2.13.0**, **2.12.0**, **2.11.0**, **2.10.0**, **2.9.0**, **2.8.0**, **2.7.0**, **2.6.0**, **2.5.0** and **2.4.0**. Read `INSTALL_STEPS.md`, sections 9.18, 9.17, 9.16 and 9.15 of `INSTRUCTION.md`, `MOBILE.md`, `MODULES.md`, `SECURITY.md` and `PRODUCTION_CHECKLIST.md` before production. The license is `LICENSE`.

### What is in the tree

| Part | Stack | Role |
| --- | --- | --- |
| API and bot | Python, FastAPI, aiogram, PostgreSQL, Redis | Shop, payments, VPN provisioning, background jobs |
| Admin | React, Vite | Plans, constructor, nodes, platform, payments, cabinet |
| Mini App | React, Vite, Telegram WebApp | Purchase inside Telegram |
| User cabinet | React, Vite | Sign-in with email, Telegram, VK and Yandex |
| Android and iOS | Kotlin Compose, SwiftUI | Buyer and administrator, Russian and English |
| Edge | Docker Compose, Caddy | HTTPS and separate domains |
| Checks | `tests/`, `scripts/sandbox-e2e.sh` | Regression and a run without live gateways |

### What 3.1.4 adds

- **The first boot no longer drops the API.** Backend and worker no longer create `alembic_version` at the same time. If a container still does not start, the installer prints the backend and worker logs instead of only `installation failed at line 382`.
- Answers are trimmed. The time zone `Moscow` is stored as `Europe/Moscow`.
- The schema stays `0038_v2_6_0_platform`. The Android buyer app stays **2.10.0** and the administrator app stays **2.12.0**. Details are in section 9.18 of `INSTRUCTION.md` and in `RELEASE_NOTES_V3_1_4.md`.

### What 3.1.3 adds

- **`curl | bash` waits for answers.** The pipe is occupied by the script, so questions are read from the SSH terminal. In 3.1.2 the first question ended with `installation failed at line 34`.
- The schema stays `0038_v2_6_0_platform`. The Android buyer app stays **2.10.0** and the administrator app stays **2.12.0**. Details are in section 9.17 of `INSTRUCTION.md` and in `RELEASE_NOTES_V3_1_3.md`.

### What 3.1.2 adds

- **VPN keys are hidden from role viewer.** A Remnawave subscription and connection keys require `users.keys`. User lists and the user card omit the subscription URL and passwords. Overview shows only the user total.
- **Panel responses omit exception text.** Diagnostics, jobs, backups, providers, payouts, monitors, the audit log, and refund reasons do not return stderr or exception strings. The detail stays in the process log.
- **Remnawave user UUIDs.** The user card, extension, subscription, and keys accept a string identifier.
- The schema stays `0038_v2_6_0_platform`. The Android buyer app stays **2.10.0** and the administrator app stays **2.12.0**. Details are in section 9.16 of `INSTRUCTION.md` and in `RELEASE_NOTES_V3_1_2.md`.

### What 3.1.1 adds

- **Staging secrets are kept.** Saving **Проверка тестового контура** (Staging checks) again leaves a blank secret, Shop ID, or Merchant ID as the value already stored. A match with the `.env` keys is still rejected.
- **The payment URL is in the log.** The runner prints `[CHECKOUT]` and an https link. Status `awaiting_checkout` does not open the production gate. **Разрешить реальные платежи** (Allow live payments) waits for `FULL_E2E_PASS` younger than 24 hours. The order is section 9.15 of `INSTRUCTION.md`.
- **The log hides secrets.** Before the status is stored, tokens and secrets of 8 characters or more are replaced with `[скрыто]`.
- **Step-by-step install.** `INSTALL_STEPS.md` lists every prompt from `install.sh` and `deploy/install-vps.sh`.
- The schema stays `0038_v2_6_0_platform`. The Android buyer app stays **2.10.0** and the administrator app stays **2.12.0**. Details are in `RELEASE_NOTES_V3_1_1.md`.

### What 3.1.0 adds

- **The public plan list** no longer returns `remnawave_profile_id`. The profile id stays in the administrator panel and on the payment snapshot.
- **Auto-renew status** for the buyer answers «Автопродление не выполнено» when a renewal failed. The exception text stays in the database and in the log.
- **Package checksum.** An APK or IPA upload stores SHA-256. The cabinet and the panel show it only next to a download link. The stored file name stays hidden.
- **Subscription file.** `GET /api/me/subscription-file` returns the subscription URL as `remnawave-subscription.txt`. In the cabinet Connection tab the button is **Скачать подписку** (Download subscription).
- **Install guide.** `GET /api/public/apps/install` returns the shop cards, the official GitHub links and the steps in Russian and English.
- The schema stays `0038_v2_6_0_platform`. The Android buyer app stays **2.10.0** and the administrator app stays **2.12.0**. Details are in section 9.14 of `INSTRUCTION.md` and in `RELEASE_NOTES_V3_1_0.md`.

### How to download the Android and iOS apps

The project packages and the file an administrator uploaded to your shop are different links. The cabinet serves the uploaded file. The links below are the builds from this repository.

**Android buyer 2.10.0**

1. Download the APK: https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.10.0/remnawave_vpn_shop_android_user_2_10_0.apk
2. Download the checksum: https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.10.0/remnawave_vpn_shop_android_user_2_10_0.apk.sha256
3. In the directory that holds both files, run `sha256sum -c remnawave_vpn_shop_android_user_2_10_0.apk.sha256`.
4. On the phone, allow installation from the source you chose and open the APK.
5. When a shop administrator has uploaded their own APK, the cabinet **Скачать** (Download) button on the Android card opens `GET /api/public/apps/android-user/download`. The checksum of that file is shown beside the button.

**Android administrator 2.12.0**

1. Download the APK: https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.12.0/remnawave_vpn_shop_android_admin_2_12_0.apk
2. Download the checksum: https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.12.0/remnawave_vpn_shop_android_admin_2_12_0.apk.sha256
3. In the same directory, run `sha256sum -c remnawave_vpn_shop_android_admin_2_12_0.apk.sha256`.
4. In the panel, the Apps tab, the block **Скачать приложение администратора** (Download the administrator app) serves the file an administrator uploaded: `GET /api/admin/apps/android-admin/download`. The session needs the `read` permission.

**iOS**

GitHub releases do not include an IPA. A shop administrator can upload a signed IPA. The buyer cabinet then opens `GET /api/public/apps/ios-user/download`, and the panel opens `GET /api/admin/apps/ios-admin/download`. Build and sign the package in Xcode on macOS from `mobile/ios-user` and `mobile/ios-admin`.

The public summary is `GET /api/public/apps/install`.

### What 3.0.1 adds

- **Auto-renew and encrypted backups.** Secrets are decrypted with `decrypt_secret` from the `app` package. The container no longer imports `backend.app.security`, which made renewal and backup validation fail.
- **The wallet is debited once.** `POST /api/me/wallet/spend` requires `Idempotency-Key`. The same key returns the payment already created. A different key for the same purchase within 30 seconds receives 409 and does not debit the balance again. Gift purchase re-checks the key while the user row is locked.
- **A second invoice for the same purchase.** A new `Idempotency-Key` within 30 seconds does not open another provider session while the previous invoice for the same plan snapshot is still being created or is waiting for payment.
- The schema stays `0038_v2_6_0_platform`. The Android buyer app stays **2.10.0** and the administrator app stays **2.12.0**. Details are in section 9.13 of `INSTRUCTION.md`, in `SECURITY.md` and in `RELEASE_NOTES_V3_0_1.md`.

### What 3.0.0-realise adds

- **App packages up to 80 MB.** `POST /api/admin/apps/{id}/file` is no longer cut by the global 12 MB body ceiling when the request has `Content-Length`. A request without `Content-Length` stays at 12 MB. The `manage_content` permission is checked before the file is read.
- **Secrets stay off environment proxies.** Telegram, Yandex OAuth and Remnawave HTTP clients set `trust_env=False`.
- **Client address.** `X-Forwarded-For` is used only when the immediate peer is loopback, private or link-local (Caddy). A direct client cannot supply a webhook allowlist address.
- **Responses omit exception text.** Provisioning retry and the health summary do not return the exception string. The detail stays in the process log.
- The database schema stays `0038_v2_6_0_platform`. The buyer Android app stays **2.10.0**. The administrator Android app stays **2.12.0**. Details are in section 9.12 of `INSTRUCTION.md` and in `RELEASE_NOTES_V3_0_0.md`.

### What 2.13.0 adds

- **App downloads.** The admin Apps tab links to the administrator app. The user cabinet links to the buyer app. An administrator uploads an APK or IPA and edits the card text, visibility and https link. Details are in section 9.11 of `INSTRUCTION.md` and in `RELEASE_NOTES_V2_13_0.md`.
- The database schema stays `0038_v2_6_0_platform`. The buyer Android app stays **2.10.0**. The administrator Android app stays **2.12.0**.

### What 2.12.0 adds

- **Telegram mass broadcast.** The web Marketing section and the Android and iOS administrator apps queue a message with `POST /api/admin/broadcasts`. The bot process delivers it. The audience is everyone with Telegram, an active subscription, or no active subscription. A button and an image accept only `https://`. `POST /api/admin/broadcasts/{id}/retry` continues from the saved counter. The full walkthrough is `RELEASE_NOTES_V2_12_0.md` and section 9.10 of `INSTRUCTION.md`.
- Android administrator app: `versionName` **2.12.0**, `versionCode` **2120**. iOS administrator app: `MARKETING_VERSION` **2.12.0**. The buyer app stays **2.10.0**. The database schema stays `0038_v2_6_0_platform`.

### What 2.11.0 adds

- **Bilingual GitHub documents.** This README and the install, module, security and mobile guides are written in Russian and in English.
- **Update the whole project from GitHub.** On the server run `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`. The script downloads the `full_release` zip and the matching `.sha256` from GitHub only. It rejects another host, a symlink, a `..` path and an archive larger than 80 MB. `.env` stays in place. `scripts/update.sh` snapshots the current install and runs `pg_dump` before it copies the new files. A failed build restores that snapshot. The API process does not extract the archive. The admin Releases tab reads `GET /api/admin/github-update`. Cron is not enabled.
- The database schema stays `0038_v2_6_0_platform`. The license file stays `LICENSE`. The buyer and administrator APKs stay the **2.10.0** release packages.

### What 2.10.0 added

Release-signed sideload APKs `remnawave_vpn_shop_android_user_2_10_0.apk` and `remnawave_vpn_shop_android_admin_2_10_0.apk`, `versionCode` 2100. The certificate is in `RELEASE_NOTES_V2_10_0.md`. A 2.9.0 debug APK must be uninstalled once before 2.10.0. The private key is not in the release.

The buyer app shows a subscription QR from `GET /api/me/connection-qr` and opens Happ, v2rayNG and Streisand for an `https://` subscription URL. The device list omits `device_key` and `last_ip`. Traffic falls back to the subscription snapshot limit. Gift redeem and wallet top-up work, including provider `sandbox` when `PAYMENTS_SANDBOX=true`.

Mobile calls send HMAC `X-Shop-Proof`. A saved token is locked with biometrics or the device PIN. `MOBILE_REQUIRE_PROOF=false` keeps 2.9.0 apps working. Telegram notices cover expiry, top-up and a successful payment. A send failure does not roll back the payment.

The administrator app can enable a plan, open a payment card without the provider error text, and see a stale agent. iOS sources use `MARKETING_VERSION` 2.10.0. The IPA is built in Xcode on macOS. This release has no IPA.

### What 2.9.0 added

The GitHub release attached two debug-signed sideload APKs, `remnawave_vpn_shop_android_user_2_9_0.apk` and `remnawave_vpn_shop_android_admin_2_9_0.apk`. Rebuild with `scripts/build-android-apk.sh`. iOS sources open in Xcode. A payment URL opens only for `https`, or for `http` on `localhost`, `127.0.0.1` and `10.0.2.2`. The 2.9.0 User-Agent strings are `RemnawaveShop-Android-User/2.9.0`, `RemnawaveShop-Android-Admin/2.9.0`, `RemnawaveShop-iOS-User/2.9.0` and `RemnawaveShop-iOS-Admin/2.9.0`.

### What 2.8.0 added

The admin **Приложения** tab stores Russian and English card text, a link and visibility for the four apps. One PNG, JPG or WEBP logo is shown in the buyer cabinet and in the apps. The panel logo stays in **Брендинг панели**. `GET /api/public/apps` returns only enabled buyer cards.

### What 2.7.0 added

Four apps: `mobile/android-user`, `mobile/android-admin`, `mobile/ios-user`, `mobile/ios-admin`. The buyer pays, builds a tariff, sees servers and copies the subscription link. The administrator reads the overview, payments and monitoring and reviews violations. The RU/EN switch uses `mobile/l10n/user.json` and `mobile/l10n/admin.json`. Header `X-Shop-Client` receives `access_token` in JSON. Web sign-in keeps the JWT in an HttpOnly cookie. The license is the same `LICENSE` file. See `MOBILE.md`.

### What 2.6.0 added

The **Платформа** tab scores subscription sharing, lists node agents, an HWID blacklist, API keys, outbound webhooks and country counts. A secret is shown once. `scripts/node-agent.py` sends a heartbeat. The node may apply only `throttle` and `clear`, and only when `AGENT_APPLY_TC=1`. The SMTP test sends mail to the administrator who pressed the button. DKIM returns a TXT record. Extra Prometheus lines and `deploy/grafana/vpnshop-platform.json` cover the platform. The cabinet can be installed to the home screen via `cabinet/public/manifest.webmanifest`. Admin themes: dark, light, midnight, graphite, lagoon, amber, paper. The license is Remnawave VPN Shop Proprietary License 1.0.

### What 2.5.0 added

**Конструктор тарифов.** An administrator sets a base price and options for devices, traffic (0 means unlimited) and days. The buyer combines them in the cabinet and in the Mini App. The price is the base plus the chosen options. The duration, traffic and device snapshot is stored on the payment. A public or buyer server response contains no address, token or raw panel JSON. `PAYMENTS_SANDBOX=true` and `bash scripts/sandbox-e2e.sh` exercise the shop without live YooKassa, Platega or RollyPay.

2.4.0 remains: the user cabinet, tab CMS, Android / iOS / TV / computer guides, wallet, gifts, trial, promo codes, referrals, auto-renew, RBAC, 2FA and backups.

### Quick start

```bash
cp .env.example .env
# Fill APP_SECRET, the database password, BOT_TOKEN, REMNAWAVE_*, ADMIN_*,
# API_DOMAIN, ADMIN_DOMAIN, APP_DOMAIN, CABINET_DOMAIN.
# For a gateway-free check: PAYMENTS_SANDBOX=true
docker compose up -d --build
bash scripts/sandbox-e2e.sh
```

One-command install on Debian/Ubuntu:

```bash
sudo bash install.sh
```

Update an existing install from GitHub:

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

The full procedure is `INSTRUCTION.md`, section 9.9. Do not commit `.env`, tokens or passwords.

### Documentation

| File | Contents |
| --- | --- |
| `INSTRUCTION.md` | Full RU/EN guide, including the gateway-free test and the GitHub update |
| `MODULES.md` | Why each module exists, RU/EN |
| `FUNCTIONS.md` | Function map, RU/EN |
| `SECURITY.md` | Security model, RU/EN |
| `DOCUMENTATION.md` | Index of current documents and archived audits |
| `LICENSE` | Proprietary license 1.0, RU/EN |
| `MOBILE.md` | Android and iOS functions, session, logo and build, RU/EN |
| `RELEASE_NOTES_V3_1_0.md` | 3.1.0 audit, checksum and app download steps |
| `RELEASE_NOTES_V3_0_1.md` | 3.0.1 audit: auto-renew, backups and wallet |
| `RELEASE_NOTES_V3_0_0.md` | 3.0.0-realise audit and checklist result |
| `RELEASE_NOTES_V2_13_0.md` | 2.13.0 app downloads |
| `RELEASE_NOTES_V2_12_0.md` | 2.12.0 broadcast, function reference and the check |
| `RELEASE_NOTES_V2_11_0.md` | 2.11.0 documents and the safe update order |
| `INSTALL.md` | Installer, RU/EN |
| `PRODUCTION_CHECKLIST.md` | Production checklist |
| `.env.example` | Environment variables |

### Local check

```bash
python3 -m compileall -q backend
python3 -m pytest -q
bash -n install.sh deploy/install-vps.sh scripts/sandbox-e2e.sh scripts/update.sh scripts/update-from-github.sh
cd admin && npm ci && npx vite build
cd ../miniapp && npm install && npx vite build
cd ../cabinet && npm install && npx vite build
```

### License

**Remnawave VPN Shop Proprietary License 1.0** (`SPDX-License-Identifier: LicenseRef-Proprietary`). The full Russian and English text is `LICENSE`.

Reading the repository is allowed. Copying, modifying, redistributing, or offering the software as a service needs a written grant from the repository owner booarkz-cpu/remnawave-vpn-shop. The program is provided as is, without warranties.
