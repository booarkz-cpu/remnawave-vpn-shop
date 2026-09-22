# Remnawave VPN Shop 2.10.0

Платформа магазина VPN: Telegram-бот, Mini App, отдельный личный кабинет, админ-панель Material Design + Web 3.0, отдельные приложения Android и iOS для покупателя и администратора, API, платежи YooKassa / Platega / RollyPay и sandbox без шлюзов, конструктор тарифа, статус узлов Remnawave, антиабьюз, агент узла, выдача доступа, очереди и резервные копии.

The same product in English: a VPN shop with a Telegram bot, a Mini App, a standalone user cabinet, an admin console, separate Android and iOS apps for buyers and administrators, a FastAPI backend, three payment providers plus a sandbox provider, a tariff constructor, Remnawave node status, abuse scoring, a node agent, provisioning, queues and backups.

Состояние: **2.10.0**. Предыдущие релизы: **2.9.0**, **2.8.0**, **2.7.0**, **2.6.0**, **2.5.0** и **2.4.0**. Перед production пройдите `INSTRUCTION.md`, `MOBILE.md`, `MODULES.md`, `SECURITY.md` и `PRODUCTION_CHECKLIST.md`. Лицензия — `LICENSE`.

Current release: **2.10.0**. Previous releases: **2.9.0**, **2.8.0**, **2.7.0**, **2.6.0**, **2.5.0** and **2.4.0**. Read `INSTRUCTION.md`, `MOBILE.md`, `MODULES.md`, `SECURITY.md` and `PRODUCTION_CHECKLIST.md` before production. The license is `LICENSE`.

## Состав

| Часть | Технология | Зачем |
| --- | --- | --- |
| API и бот | Python, FastAPI, aiogram, PostgreSQL, Redis | Магазин, платежи, выдача VPN, фоновые задачи |
| Админка | React, Vite | Тарифы, конструктор, узлы, платформа, платежи и кабинет |
| Mini App | React, Vite, Telegram WebApp | Покупка внутри Telegram |
| Личный кабинет | React, Vite | Вход по email, Telegram, VK и Яндексу |
| Android и iOS | Kotlin Compose, SwiftUI | Покупатель и администратор, русский и английский |
| Периметр | Docker Compose, Caddy | HTTPS и разделение доменов |
| Проверки | `tests/`, `scripts/sandbox-e2e.sh` | Регрессия и прогон без живых касс |

## Возможности 2.10.0

- **Release APK.** `remnawave_vpn_shop_android_user_2_10_0.apk` и `remnawave_vpn_shop_android_admin_2_10_0.apk`, `versionCode` 2100. Сертификат и контрольные суммы — в `RELEASE_NOTES_V2_10_0.md`. Пакеты 2.9.0 были debug-подписаны, перед 2.10.0 их удаляют один раз. Закрытый ключ в релиз не входит.
- **Один шаг подключения.** QR `GET /api/me/connection-qr` и кнопки Happ, v2rayNG, Streisand для `https://` ссылки подписки.
- **Устройства, трафик, подарок и пополнение.** Список устройств без `device_key` и `last_ip`. Трафик с запасным лимитом из снимка. Подарок и пополнение кошелька, включая sandbox при `PAYMENTS_SANDBOX=true`.
- **Подпись клиента и биометрия.** HMAC `X-Shop-Proof`. Сохранённый токен закрывается биометрией или PIN. `MOBILE_REQUIRE_PROOF=false` оставляет рабочими приложения 2.9.0.
- **Telegram.** Срок подписки, пополнение и успешная оплата. Ошибка отправки не откатывает платёж.
- **Дежурство в приложении администратора.** Включение тарифа, карточка платежа без текста ошибки провайдера, признак устаревшего агента.
- **Обновление с GitHub на хосте.** `GET /api/admin/github-update` только показывает статус. Применение: `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`. Скрипт сверяет SHA-256, сохраняет `.env` и вызывает `scripts/update.sh`. API архив не распаковывает. Cron не включён по умолчанию.
- **iOS.** Исходники с `MARKETING_VERSION` 2.10.0. IPA в этом релизе нет: сборка идёт в Xcode на macOS.
- Схема базы остаётся `0038_v2_6_0_platform`. Лицензия прежняя, файл `LICENSE`.

English: release-signed sideload APKs, subscription QR and client deep links, devices and traffic, gift redeem and wallet top-up, HMAC client proof, biometric lock of a saved token, Telegram notices, admin plan toggle and payment detail, and a host script that updates from GitHub after a SHA-256 check. The API does not extract the archive. There is no IPA in this release.

## Возможности 2.9.0

- **APK для Android.** Релиз GitHub содержит два debug-подписанных пакета для ручной установки: покупатель `remnawave_vpn_shop_android_user_2_9_0.apk` и администратор `remnawave_vpn_shop_android_admin_2_9_0.apk`. Повторная сборка — `scripts/build-android-apk.sh`.
- **iOS.** Исходники `mobile/ios-user` и `mobile/ios-admin` открываются в Xcode на macOS. IPA собирается там же. В архиве этого релиза IPA нет.
- Платёжная ссылка в приложении покупателя открывается после разбора адреса: `https`, либо `http` только для `localhost`, `127.0.0.1` и `10.0.2.2`.
- User-Agent приложений: `RemnawaveShop-Android-User/2.9.0`, `RemnawaveShop-Android-Admin/2.9.0`, `RemnawaveShop-iOS-User/2.9.0`, `RemnawaveShop-iOS-Admin/2.9.0`.
- Схема базы остаётся `0038_v2_6_0_platform`. Лицензия прежняя, файл `LICENSE`.

## Возможности 2.8.0

- **Каталог приложений.** Вкладка админки «Приложения»: тексты на русском и английском, ссылка и видимость для Android и iOS покупателя и администратора.
- **Логотип кабинета и приложений.** Загрузка PNG/JPG/WEBP. Кабинет покупателя и четыре приложения показывают один и тот же файл. Логотип самой панели задаётся отдельно в «Брендинг панели».
- Публичный ответ `GET /api/public/apps` содержит только включённые карточки покупателя.

## Возможности 2.7.0

- **Четыре приложения.** `mobile/android-user`, `mobile/android-admin`, `mobile/ios-user`, `mobile/ios-admin`. Покупатель покупает тариф, собирает конструктор, видит серверы и копирует ссылку подписки. Администратор смотрит обзор, платежи, мониторинг и разбирает нарушения.
- **Язык в приложении.** Переключатель RU/EN. Каталоги `mobile/l10n/user.json` и `mobile/l10n/admin.json`.
- **Сессия.** Заголовок `X-Shop-Client` получает `access_token` в JSON. Веб-вход остаётся на HttpOnly cookie и токен в JSON не кладёт.
- **Лицензия приложений.** Тот же файл `LICENSE`, Remnawave VPN Shop Proprietary License 1.0. Разбор функций — `MOBILE.md`.

## Возможности 2.6.0

- **Платформа.** Вкладка «Платформа»: скоринг разделения подписки, агенты узлов, чёрный список HWID, ключи API, исходящие webhook, счётчики стран. Секрет показывается один раз.
- **Агент узла.** `scripts/node-agent.py` отправляет heartbeat и наблюдения. Действия на узле — только `throttle` и `clear`, и только если на узле задан `AGENT_APPLY_TC=1`.
- **Почта и метрики.** Тестовое SMTP-письмо уходит администратору, который нажал кнопку. DKIM выдаёт TXT-запись. `/metrics` добавляет три ряда, дашборд лежит в `deploy/grafana/vpnshop-platform.json`.
- **Кабинет на домашний экран.** `cabinet/public/manifest.webmanifest`.
- **Семь тем админки:** dark, light, midnight, graphite, lagoon, amber, paper.
- **Лицензия.** Remnawave VPN Shop Proprietary License 1.0, файл `LICENSE`, русский и английский текст.

## Возможности 2.5.0

- **Конструктор тарифов.** Администратор задаёт базовую цену и пункты: число устройств, объём трафика (0 = безлимит) и срок в днях. Покупатель собирает комбинацию в кабинете и в Mini App. Цена = база + выбранные пункты. Снимок срока, трафика и устройств записывается в платёж и не меняется, если конструктор потом отредактируют.
- **Мониторинг Remnawave.** В админке вкладка «Мониторинг Remnawave» показывает доступность панели, задержку и статус узлов. Покупатель видит отдельный раздел «Серверы» и краткий статус на обзоре. Публичный и пользовательский ответы не содержат адресов, токенов и сырого JSON панели.
- **Проверка до релиза без касс.** `PAYMENTS_SANDBOX=true` и `bash scripts/sandbox-e2e.sh`. Живые YooKassa, Platega и RollyPay для этого прогона не нужны.
- Интерфейсы и документы GitHub на **русском и английском**.

Уже было в 2.4.0 и сохранено: личный кабинет, CMS вкладок, инструкции Android / iOS / TV / компьютер, кошелёк, подарки, пробный период, промокоды, рефералы, автопродление, RBAC, 2FA, бэкапы.

## Быстрый старт

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

Подробности — в `INSTRUCTION.md`. Не коммитьте `.env`, токены и пароли.

## Документация

| Файл | Содержание |
| --- | --- |
| `INSTRUCTION.md` | Полная инструкция RU/EN, включая тест без касс |
| `MODULES.md` | Каждый модуль и зачем он нужен, RU/EN |
| `FUNCTIONS.md` | Разбор функций кода |
| `SECURITY.md` | Модель безопасности RU/EN |
| `DOCUMENTATION.md` | Карта актуальных документов и архивных аудитов |
| `LICENSE` | Проприетарная лицензия 1.0, RU/EN |
| `MOBILE.md` | Android и iOS: функции, сессия, логотип, сборка, RU/EN |
| `RELEASE_NOTES_V2_10_0.md` | Что вошло в 2.10.0, release APK, подпись клиента и обновление с GitHub |
| `RELEASE_NOTES_V2_9_0.md` | Что вошло в 2.9.0, APK и сборка iOS |
| `RELEASE_NOTES_V2_8_0.md` | Что вошло в 2.8.0 |
| `RELEASE_NOTES_V2_7_0.md` | Что вошло в 2.7.0 |
| `RELEASE_NOTES_V2_6_0.md` | Что вошло в 2.6.0 и границы реализации |
| `RELEASE_NOTES_V2_5_0.md` | Что вошло в 2.5.0 и чего нет из внешних проектов |
| `INSTALL.md` | Установщик |
| `PRODUCTION_CHECKLIST.md` | Чеклист production |
| `.env.example` | Переменные окружения |

## Локальная проверка

```bash
python3 -m compileall -q backend
python3 -m pytest -q
bash -n install.sh deploy/install-vps.sh scripts/sandbox-e2e.sh
cd admin && npm ci && npx vite build
cd ../miniapp && npm install && npx vite build
cd ../cabinet && npm install && npx vite build
```

## Лицензия

**Remnawave VPN Shop Proprietary License 1.0** (`SPDX-License-Identifier: LicenseRef-Proprietary`). Полный текст на русском и английском — в `LICENSE`.

Чтение репозитория разрешено. Копирование, изменение, распространение и запуск как услуги для третьих лиц требуют письменного разрешения владельца репозитория booarkz-cpu/remnawave-vpn-shop. Программа поставляется «как есть», без гарантий.

English: reading the repository is allowed. Copying, modifying, redistributing, or offering the software as a service needs a written grant from the repository owner. See `LICENSE`.
