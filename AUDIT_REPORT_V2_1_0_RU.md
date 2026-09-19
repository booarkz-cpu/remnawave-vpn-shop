# Полный аудит и hardening — Remnawave VPN Shop 2.1.0

## Результат

Релиз 2.1.0 — это production-hardening поверх 2.0.4. Проверены backend/API, worker, PostgreSQL/Alembic, платежи и webhooks, возвраты, рефералы, автопродление, provisioning Remnawave, авторизация/MFA/CSRF/RBAC, privacy, SSRF/DNS pinning, backup/restore, Docker/Compose, release tooling и клиентские приложения.

## Что добавлено

1. Идемпотентная финансовая книга (`financial_ledger`) для платежей и возвратов.
2. Корреляция запросов через `X-Request-ID` и request ID в audit log.
3. Структурированные HTTP-логи с request ID, методом, маршрутом, статусом и клиентом.
4. Раздельные `/health/live` и `/health/ready`.
5. Корректное завершение фоновых задач API-процесса.
6. Защита финансовых операций от повторной записи уникальным operation key.
7. Единый release identity 2.1.0 и актуальный migration head 0033.
8. Исправлен default artifact в `verify-release.sh`.
9. Усилены CI-проверки frontend/backend и security tooling.
10. Панель и Mini App переведены на понятный русский интерфейс; исторические V44-документы сохранены как архив.

## Ограничения проверки

В локальной среде отсутствовали Docker daemon и внешний доступ к некоторым registry/API. Поэтому live-платежи, реальные webhooks, реальное восстановление PostgreSQL и production staging не объявляются пройденными автоматически. Эти проверки описаны в `E2E_PROCEDURE_RU.md`.
