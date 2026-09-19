# Remnawave VPN Shop 2.2.1

> **Status: 🚧 In active development — not a final production release.**

Полноценная платформа VPN-магазина с Telegram Mini App, административной панелью, backend API, платежами, провижинингом Remnawave, очередями задач, мониторингом и инструментами эксплуатации.

## Состав проекта

- **Backend:** Python / FastAPI, PostgreSQL, Redis
- **Admin:** React + Vite
- **Mini App:** React + Vite / Telegram WebApp
- **Infrastructure:** Docker Compose, Caddy, VPS deployment scripts
- **Operations:** backup/restore, health checks, preflight/security checks, rollback и release tooling
- **Tests:** regression, production и release-quality тесты

## Возможности

Проект включает подписки, мультиустройства, автопродление, промокоды и подарки, реферальную программу, поддержку, уведомления, антифрод, финансовый журнал, мониторинг, управление узлами Remnawave, резервное копирование и восстановление, аудит действий и production security hardening.

## Текущий статус

Версия в архиве: **2.2.1**.

Проект продолжает развиваться. Возможны незавершённые функции, изменения API/конфигурации и изменения deployment-процесса. Перед использованием в production необходимо самостоятельно пройти процедуры из `INSTALL.md`, `PRODUCTION_CHECKLIST.md` и актуальных audit/release документов.

## Быстрый старт

1. Скопировать `.env.example` в `.env` только для локальной настройки.
2. Задать реальные секреты и параметры окружения.
3. Ознакомиться с `INSTALL.md`.
4. Для production использовать deployment-инструкции и preflight-проверки из `deploy/` и `scripts/`.

**Никогда не коммитьте `.env`, реальные токены, пароли или приватные ключи.**

## Документация

- `INSTALL.md` — установка
- `PRODUCTION_CHECKLIST.md` — production checklist
- `OPERATIONS_RUNBOOK_RU.md` — эксплуатация
- `API_REFERENCE_RU.md` — API
- `SECURITY_MODEL_RU.md` — модель безопасности
- `AUDIT_REPORT_V2_2_1_RU.md` — актуальный аудит
- `RELEASE_DOCUMENTATION_INDEX_RU.md` — индекс release-документации

## Contributing

Проект находится в разработке. Issues и pull requests приветствуются. Перед внесением изменений рекомендуется ознакомиться с документацией, тестами и release/audit материалами.

## License

License не указан в исходном архиве. Использование и распространение следует согласовать с владельцем проекта до публичного релиза.
