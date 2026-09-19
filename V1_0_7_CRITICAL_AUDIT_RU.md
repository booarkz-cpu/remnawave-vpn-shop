# V1.0.7-realise — Critical Audit

Дата: 2026-09-14

## Результат

Проведён повторный критический аудит исходников V1.0.6-realise с фокусом на финансовые state transitions, distributed locks, удалённое provisioning и race conditions.

### CRITICAL — stale User snapshot после захвата user lock

В `fulfill()` первоначальная выборка `User` выполнялась до получения `lock:fulfill:user:<id>`. Если удаление аккаунта успевало завершиться между этой выборкой и захватом lock, объект `User` в SQLAlchemy session мог оставаться со старым `deleted_at=None`.

При этом последующая логика уже защищалась lock-ом, но использовала stale snapshot и могла начать внешний Remnawave provisioning для уже удалённого/anonymized аккаунта.

### Исправление

После получения user lock `fulfill()` теперь:

1. перечитывает `User` через `SELECT ... FOR UPDATE`;
2. проверяет `deleted_at`;
3. повторно получает актуальный `Plan`;
4. пересчитывает checkout snapshot fallback-параметры;
5. только после этого захватывает payment lock и допускает внешний side effect.

Это закрывает TOCTOU между discovery read и критической секцией.

## Регрессия

Добавлены тесты `tests/test_v1_0_7_critical_regression.py`, фиксирующие порядок:

`user lock → User FOR UPDATE/recheck → payment lock → external provisioning`

## Верификация

- pytest: **249 passed**
- Python compileall: PASS
- shell syntax: PASS
- Docker Compose YAML: PASS
- ZIP integrity: PASS
- SHA-256: generated and independently verified by build script

## Ограничения

Live production E2E с реальными credentials платёжных провайдеров и живым Remnawave не выполнялся в данной среде. Полный Vite production build без установленных frontend dependencies не заявляется как выполненный.
