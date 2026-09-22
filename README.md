# Remnawave VPN Shop 2.5.0

Платформа магазина VPN: Telegram-бот, Mini App, отдельный личный кабинет, админ-панель Material Design + Web 3.0, API, платежи YooKassa / Platega / RollyPay и sandbox без шлюзов, конструктор тарифа, статус узлов Remnawave, выдача доступа, очереди и резервные копии.

The same product in English: a VPN shop with a Telegram bot, a Mini App, a standalone user cabinet, an admin console, a FastAPI backend, three payment providers plus a sandbox provider, a tariff constructor, Remnawave node status, provisioning, queues and backups.

Состояние: **2.5.0**. Предыдущий релиз: **2.4.0**. Перед production пройдите `INSTRUCTION.md`, `MODULES.md` и `PRODUCTION_CHECKLIST.md`.

## Состав

| Часть | Технология | Зачем |
| --- | --- | --- |
| API и бот | Python, FastAPI, aiogram, PostgreSQL, Redis | Магазин, платежи, выдача VPN, фоновые задачи |
| Админка | React, Vite | Управление тарифами, конструктором, узлами, платежами и кабинетом |
| Mini App | React, Vite, Telegram WebApp | Покупка внутри Telegram |
| Личный кабинет | React, Vite | Вход по email, Telegram, VK и Яндексу |
| Периметр | Docker Compose, Caddy | HTTPS и разделение доменов |
| Проверки | `tests/`, `scripts/sandbox-e2e.sh` | Регрессия и прогон без живых касс |

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

В архиве лицензия не указана. Использование согласуйте с владельцем репозитория.
