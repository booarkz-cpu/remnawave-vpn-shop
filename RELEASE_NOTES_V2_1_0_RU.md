# Релиз 2.1.0 — Production Hardening

## Главное

- финансовый immutable ledger для платежей и возвратов;
- request ID во всех HTTP-ответах и audit log;
- структурированные журналы запросов;
- liveness/readiness health endpoints;
- корректная остановка фоновых задач;
- единый и проверяемый release identity;
- усиленный CI и security pipeline;
- русскоязычный интерфейс админ-панели и Mini App;
- документация переработана для установки, эксплуатации, восстановления и аудита.

## Миграция

Перед запуском production выполните `alembic upgrade head`. Новая голова миграций: `0033_v2_1_0_production_hardening`.
