# Remnawave VPN Shop 2.4.0

Платформа магазина VPN: Telegram Mini App, отдельный личный кабинет пользователя, админ-панель Material Design + Web 3.0, API, платежи YooKassa / Platega / RollyPay и sandbox без шлюзов, выдача доступа в Remnawave, очереди, резервные копии и мониторинг.

The same product in English: a VPN shop with a Telegram Mini App, a standalone user cabinet, an admin console, a FastAPI backend, three payment providers plus a sandbox provider, Remnawave provisioning, backups and monitoring.

Состояние: **2.4.0**. Перед production пройдите `INSTRUCTION.md` и `PRODUCTION_CHECKLIST.md`. Предыдущая линейка 2.3.0 остаётся в истории релизов.

## Состав

| Часть | Технология |
| --- | --- |
| API и бот | Python, FastAPI, aiogram, PostgreSQL, Redis |
| Админка | React, Vite, Material + Web3 UI |
| Mini App | React, Vite, Telegram WebApp |
| Личный кабинет | React, Vite, email / Telegram / VK / Яндекс |
| Периметр | Docker Compose, Caddy |
| Проверки | `tests/`, `scripts/sandbox-e2e.sh` |

## Возможности

Подписки и пробный период, несколько устройств, автопродление YooKassa, промокоды (включая дни), внутренний кошелёк, подарки, необязательная подписка на канал, реферальная программа, поддержка, уведомления, антифрод, финансовый журнал, мониторинг, резервное копирование, аудит, RBAC и 2FA.

В 2.4.0 добавлены: отдельный личный кабинет с регистрацией/входом, CMS вкладок кабинета в админке, инструкции по устройствам, `PAYMENTS_SANDBOX` и скрипт `scripts/sandbox-e2e.sh` для проверки без живых касс. Интерфейсы доступны на **русском и английском**.

## Быстрый старт

```bash
cp .env.example .env
# Заполните APP_SECRET, пароль БД, BOT_TOKEN, REMNAWAVE_*, ADMIN_*,
# API_DOMAIN, ADMIN_DOMAIN, APP_DOMAIN, CABINET_DOMAIN и allowlist YooKassa.
docker compose up -d --build
```

Одношаговая установка на Debian/Ubuntu:

```bash
sudo bash install.sh
```

Для проверки без платёжных шлюзов:

```bash
# в .env: PAYMENTS_SANDBOX=true
bash scripts/sandbox-e2e.sh
```

Подробности — в `INSTRUCTION.md`. Не коммитьте `.env`, токены и пароли.

## Документация

| Файл | Содержание |
| --- | --- |
| `INSTRUCTION.md` | Полная инструкция RU/EN |
| `FUNCTIONS.md` | Разбор функций |
| `SECURITY.md` | Модель безопасности |
| `RELEASE_NOTES_V2_4_0.md` | Что нового в 2.4.0 |
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

В архиве лицензия не указана. Использование согласуйте с владельцем репозитория.
