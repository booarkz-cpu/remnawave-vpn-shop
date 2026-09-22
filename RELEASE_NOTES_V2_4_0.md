# Remnawave VPN Shop 2.4.0

## Что нового

- Отдельный SPA **личный кабинет** (`cabinet/`): регистрация и вход по email+пароль, Telegram WebApp, VK ID, Яндекс ID.
- Тарифы, покупка, пробный период, ссылка подписки и инструкции для Android / iOS / TV / Windows / macOS / Linux.
- В админке вкладка **«Личный кабинет»**: CMS меню вкладок и тексты инструкций устройств.
- Админ-панель переведена на визуальный язык Material Design + Web 3.0 (charcoal + cyan, Sora / IBM Plex).
- Платёжный провайдер `sandbox` при `PAYMENTS_SANDBOX=true` и скрипт `scripts/sandbox-e2e.sh` — полный контур без YooKassa / Platega / RollyPay.
- Docker Compose и Caddy обслуживают `CABINET_DOMAIN`. Миграция `0036_v2_4_0_cabinet`.

## Критические исправления

- Восстановление админ-сессии после F5 по cookie.
- Rate limit на `/api/auth/login` и `/api/auth/register`.
- `/api/me/connection-info` отдаёт инструкции даже без активной подписки.
- TrustedHost и CORS учитывают кабинет; return URL песочницы ведёт в `CABINET_URL`.

## Миграция с 2.3.0

1. Обновите код и выполните `alembic upgrade head` (или штатный `docker compose up -d --build`).
2. Добавьте в `.env`: `CABINET_DOMAIN`, `CABINET_URL`, при необходимости `VK_*`, `PAYMENTS_SANDBOX`, `TRIAL_MAX_DAYS`.
3. Расширьте `ADMIN_CORS_ORIGINS` доменом кабинета.
4. Для тестов без касс: `PAYMENTS_SANDBOX=true` и `bash scripts/sandbox-e2e.sh`.

## Проверка релиза

- `python3 -m pytest -q`
- `python3 -m compileall -q backend`
- `bash -n install.sh deploy/install-vps.sh scripts/sandbox-e2e.sh`
