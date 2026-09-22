# Remnawave VPN Shop 2.8.0

Платформа магазина VPN: Telegram-бот, Mini App, отдельный личный кабинет, админ-панель Material Design + Web 3.0, отдельные приложения Android и iOS для покупателя и администратора, API, платежи YooKassa / Platega / RollyPay и sandbox без шлюзов, конструктор тарифа, статус узлов Remnawave, антиабьюз, агент узла, выдача доступа, очереди и резервные копии.

The same product in English: a VPN shop with a Telegram bot, a Mini App, a standalone user cabinet, an admin console, separate Android and iOS apps for buyers and administrators, a FastAPI backend, three payment providers plus a sandbox provider, a tariff constructor, Remnawave node status, abuse scoring, a node agent, provisioning, queues and backups.

Состояние: **2.8.0**. Предыдущие релизы: **2.7.0**, **2.6.0**, **2.5.0** и **2.4.0**. Перед production пройдите `INSTRUCTION.md`, `MOBILE.md`, `MODULES.md`, `SECURITY.md` и `PRODUCTION_CHECKLIST.md`. Лицензия — `LICENSE`.

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
