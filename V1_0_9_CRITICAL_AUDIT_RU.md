# V1.0.9-realise — критический аудит и исправления

Дата: 2026-09-14

## Область аудита

Проверены критические финансовые и provisioning workflows текущего V1.0.8-realise: подтверждение платежа, fulfillment, auto-renew, refund/reconciliation, Redis distributed locks, TOCTOU между удалением аккаунта и provisioning, а также regression tests и release tooling.

Методика соответствует baseline manual secure-code review: анализ архитектуры и trust boundaries, data flow, business logic, state transitions, race conditions, transaction integrity и configuration/deployment. OWASP отдельно рекомендует ручную проверку race conditions, TOCTOU и бизнес-логики. 

## 🔴 Critical #1 — runtime failure в atomic payment confirmation

### Проблема

В `_confirm_and_fulfill_payment()` результат запроса сохранялся в переменную `confirmed`, но следующая проверка обращалась к несуществующей переменной `confirmed_payment`.

Это приводило к `NameError` при любом выполнении этого критического workflow. В результате подтверждение успешного webhook/reconciliation не доходило до fulfillment.

### Исправление

Проверка приведена к фактически загруженному объекту:

```python
confirmed = (...).scalar_one_or_none()
if not confirmed:
    raise RuntimeError(...)
```

Добавлен отдельный regression test, запрещающий возвращение undefined identifier.

## 🔴 Critical #2 — stale User snapshot в fulfillment при уже удерживаемом user-lock

### Проблема

В обычном пути `fulfill()` после получения user-lock выполнял `SELECT ... FOR UPDATE` для User. Однако при вызове из auto-renew/webhook с уже переданным `existing_user_lock_token` повторного чтения User не происходило.

Это оставляло TOCTOU окно на уровне ORM snapshot:

1. User был прочитан как активный.
2. Вызывающий workflow получил user-lock.
3. Объект User оставался старым.
4. `fulfill()` мог продолжить provisioning без повторной проверки `deleted_at`.

Сам факт наличия distributed lock не заменяет повторное чтение защищаемого состояния. Для критической операции состояние должно быть проверено после входа в критическую секцию.

### Исправление

`fulfill()` теперь **всегда**, независимо от наличия `existing_user_lock_token`, выполняет:

`SELECT User ... FOR UPDATE → deleted_at check → Plan reload → payment lock → Payment FOR UPDATE → provisioning`.

Таким образом, auto-renew и другие пути с уже удерживаемым user-lock получают ту же защиту от stale User state, что и обычный fulfillment.

Добавлены regression tests на порядок операций и обязательный `FOR UPDATE`.

## Верификация

Перед релизом выполнены:

- полный pytest suite;
- отдельные V1.0.9 critical regression tests;
- Python `compileall`;
- shell syntax checks;
- Docker Compose YAML parsing;
- ZIP integrity check;
- detached SHA-256 verification.

Production E2E с реальными credentials платёжных провайдеров и живым Remnawave в данной среде не заявляется как выполненный.

## Инварианты после исправления

1. Refunded/creation-unknown payment не может быть подтверждён обратно в `paid`.
2. Успешное подтверждение платежа использует актуальный Payment под `FOR UPDATE`.
3. Fulfillment не начинает внешний Remnawave side effect для удалённого User.
4. Все критические user/payment workflows сохраняют порядок distributed locks `user → payment`.
5. Auto-renew передаёт уже удерживаемый user-lock в fulfillment, но fulfillment всё равно перечитывает User под `FOR UPDATE`.
6. Redis lock release остаётся token-safe.
