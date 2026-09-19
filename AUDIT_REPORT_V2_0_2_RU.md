# Полный критический аудит — 2.0.2-audited

Дата аудита: 2026-09-14

## Итог

Проведён повторный source-level аудит перед выпуском. Найдены и исправлены пять критических/релиз-блокирующих дефектов, два из которых ломали пользовательскую аутентификацию в runtime, один ломал исполняемость release tooling после распаковки, один делал CI Compose-gate невоспроизводимым на чистом runner, один создавал рассинхронизацию идентичности версии runtime и фактического релиза.

### Severity

| ID | Уровень | Область | Статус |
|---|---|---|---|
| C-01 | Critical | Telegram authentication | Исправлено |
| C-02 | Critical | Yandex auth exchange | Исправлено |
| C-03 | High/Critical release blocker | Executable release scripts | Исправлено |
| C-04 | High release blocker | CI Compose validation | Исправлено |
| C-05 | High release blocker | Runtime release identity | Исправлено |

## C-01 — Telegram authentication runtime failure

Endpoint `/api/auth/telegram` вызывал `create_user_session(..., request)` и `_client_ip(request)`, однако `request` не был объявлен параметром endpoint.

Воздействие: после успешной верификации Telegram `initData` пользователь не мог получить рабочую сессию.

Исправление: добавлен `request: Request`.

Regression protection: `tests/test_v2_0_1_critical_regressions.py`.

## C-02 — Yandex exchange runtime failure

Endpoint `/api/auth/exchange` создавал user session и audit event через `request`, но `Request` не был частью сигнатуры.

Воздействие: OAuth callback мог завершить выдачей exchange code, но обмен кода на рабочую user session падал.

Исправление: добавлен `request: Request`.

## C-03 — executable bits

После распаковки исходного ZIP три проверяемых shell entrypoints имели mode `0644`.

Воздействие: documented one-step/release/staging commands могли завершиться `Permission denied`.

Исправление: executable mode восстановлен; regression test проверяет mode.

## C-04 — CI Compose gate

Workflow выполнял `docker compose config` без production `.env`, при этом Compose содержит обязательные переменные.

Воздействие: чистый CI runner не мог пройти configuration gate независимо от корректности исходников.

Исправление: CI создаёт ephemeral минимальный `.env` с безопасными test values перед `docker compose config`.

## C-05 — runtime version не соответствовала выпущенному артефакту

`backend/app/main.py` продолжал объявлять `APP_VERSION = "2.0.0-realise"`, тогда как release tooling и документация выпускали `2.0.2-audited`. Это могло приводить к неверной диагностике `/health`, admin monitoring, release/update UI и API metadata.

**Исправление:** runtime version синхронизирована с контрактом `2.0.2-audited`; добавлен regression test, сверяющий runtime, build script и release manifest template.

## Проверки

1. Полный pytest suite: **271 passed**.
2. Python bytecode compilation: PASS.
3. Shell syntax: PASS.
4. AST scan для endpoint-функций с использованием `request`: PASS; необъявленных использований нет.
5. Release script executable modes: PASS.

## Дополнительный security review

Проверены исходники на:
- shell injection через subprocess;
- небезопасный `shell=True`;
- архив traversal;
- cookie/CSRF controls;
- server-side session revocation;
- JWT type/JTI validation;
- payment idempotency;
- refund locking and uncertain external outcomes;
- subscription remote revoke retry;
- gift redemption idempotency;
- provider selection/circuit breaker;
- staging runner token and HTTPS requirements;
- backup/restore subprocess boundaries.

Обнаруженные в предыдущих версиях invariants сохранены; новые исправления не требуют изменения migration head.

## Ограничения

Не выполнялись:
- live payment provider sandbox E2E;
- live Telegram Bot API;
- live Remnawave provisioning;
- container vulnerability scan через Trivy (утилита отсутствует);
- pip-audit/npm audit без lock/dependency scanner environment;
- полноценный Docker build без Docker daemon.

Эти ограничения явно не маскируются под PASS.
