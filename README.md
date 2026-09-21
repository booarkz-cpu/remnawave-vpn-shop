# Remnawave VPN Shop 2.2.1

Платформа магазина VPN: Telegram Mini App, админ-панель, API, платежи YooKassa / Platega / RollyPay, выдача доступа в Remnawave, очереди, резервные копии и мониторинг.

The same product in English: a VPN shop with a Telegram Mini App, an admin console, a FastAPI backend, three payment providers, Remnawave provisioning, backups and monitoring.

Состояние: **2.2.1, активная разработка**. Перед production пройдите `INSTRUCTION.md` и `PRODUCTION_CHECKLIST.md`.

## Состав

| Часть | Технология |
| --- | --- |
| API и бот | Python, FastAPI, aiogram, PostgreSQL, Redis |
| Админка | React, Vite |
| Mini App | React, Vite, Telegram WebApp |
| Периметр | Docker Compose, Caddy |
| Проверки | `tests/` |

## Возможности

Подписки и пробный период, несколько устройств, автопродление YooKassa, промокоды, подарки, реферальная программа, поддержка, уведомления, антифрод, финансовый журнал, мониторинг, резервное копирование, аудит действий, RBAC и необязательная 2FA.

Интерфейсы админки, Mini App и ответы бота доступны на **русском и английском**. Переключатель в интерфейсе пишет выбор в `localStorage` (`rw_lang`). Пока выбора нет, используется `DEFAULT_LANGUAGE` и язык браузера или Telegram.

## Быстрый старт

```bash
cp .env.example .env
# Заполните APP_SECRET (не короче 32 символов), пароль БД, BOT_TOKEN,
# REMNAWAVE_URL, REMNAWAVE_TOKEN, ADMIN_EMAIL, ADMIN_PASSWORD
# и allowlist IP вебхуков YooKassa.
docker compose up -d --build
```

Одношаговая установка на Debian/Ubuntu:

```bash
sudo bash install.sh
```

Подробности, первый вход, платежи, бэкапы и разбор экранов — в `INSTRUCTION.md`.

Не коммитьте `.env`, токены, пароли и приватные ключи.

## Документация

| Файл | Содержание |
| --- | --- |
| `INSTRUCTION.md` | Полная инструкция на русском и английском |
| `FUNCTIONS.md` | Разбор функций backend и интерфейсов |
| `SECURITY.md` | Модель безопасности, RU/EN |
| `SECURITY_MODEL_RU.md` | Краткая модель на русском |
| `INSTALL.md` | Установщик |
| `PRODUCTION_CHECKLIST.md` | Чеклист production |
| `.env.example` | Все переменные окружения |

## Локальная проверка

```bash
python3 -m compileall -q backend
python3 -m pytest -q
cd admin && npm ci && npx vite build
cd miniapp && npm install && npx vite build
```

## Лицензия

В архиве лицензия не указана. Использование и распространение согласуйте с владельцем репозитория до публичного релиза.
