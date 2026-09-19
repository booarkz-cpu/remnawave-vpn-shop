# V1.0.4-realise — критический аудит, исправления и выпуск

Дата: 2026-09-14

## 1. Цель

Проведён повторный baseline-аудит текущей версии проекта с приоритетом **критических ошибок**: денежные операции, provisioning, account deletion, auto-renew, refunds, distributed locks, authentication/authorization, backup/restore и внешние side effects.

Методика опирается на ручной review архитектуры, entry points, auth/RBAC, data flow, business logic, state transitions, transaction integrity и concurrency. Это соответствует OWASP Secure Code Review и Business Logic Security guidance. См. также: https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html и https://cheatsheetseries.owasp.org/cheatsheets/Business_Logic_Security_Cheat_Sheet.html

## 2. Найденная критическая ошибка

### CRITICAL — несовместимый порядок distributed locks в fulfillment и auto-renew

Компоненты:
- `fulfill()`;
- `auto_renew_scheduler()`;
- webhook/job fulfillment paths.

Проблемный сценарий:

1. обычный webhook/worker fulfillment захватывает payment lock;
2. затем пытается получить user fulfillment lock;
3. auto-renew уже удерживает user lock;
4. auto-renew пытается получить payment lock;
5. две операции конкурируют за разные lock'и.

Redis helper корректно fail-fast, а не блокируется бесконечно, но это не делает ситуацию безопасной: обычный fulfillment мог перейти в failed/retry уже после подтверждения платежа, а auto-renew — потерять окно продления. Для платёжного workflow это нарушение критического инварианта **paid payment → exactly-once/at-least-once fulfillment without avoidable lock conflict**.

### Исправление

Введён единый глобальный порядок lock acquisition:

**`user lock → payment lock`**

`fulfill()` теперь:

1. получает user lock;
2. затем payment lock;
3. выполняет provisioning;
4. освобождает payment lock;
5. освобождает user lock только если lock был захвачен самим `fulfill()`.

Если auto-renew уже передал собственный user-lock token, `fulfill()` его не освобождает.

Это устраняет конфликт между webhook/worker fulfillment и auto-renew и сохраняет сериализацию с account deletion.

## 3. Регрессионное покрытие

Добавлены проверки:

- release version consistency;
- global `user → payment` lock ordering;
- корректное освобождение caller-owned user lock;
- сохранение token-safe cleanup для renewal tasks.

## 4. Полный regression suite

**242 теста — PASS.**

Дополнительно проверено:

- `python -m compileall -q backend` — PASS;
- shell syntax — PASS;
- Docker Compose YAML parse — PASS;
- ZIP integrity — PASS;
- SHA-256 — PASS.

## 5. Повторно проверенные критические контуры

### Payments
- durable payment intent;
- DB idempotency;
- provider/order binding;
- signed/verified webhooks;
- late webhook after refund;
- payment side-effect lock;
- fulfillment retry;
- recurring payment intent.

### Provisioning
- Remnawave idempotent extension;
- remote user recovery after lost response;
- immutable plan snapshots;
- user-level serialization;
- deletion vs provisioning race.

### Refunds
- refund state machine;
- provider refund identity;
- refund/fulfillment serialization;
- remote revoke;
- referral reward reversal.

### Account security
- Telegram signed initData;
- Yandex OAuth state;
- admin sessions;
- MFA/TOTP;
- recovery codes;
- RBAC;
- CSRF;
- deleted-account token rejection.

### Infrastructure security
- Redis lock leases and token ownership;
- DNS pinning / SSRF defense;
- request body limits including chunked bodies;
- archive traversal protection;
- backup checksum and isolated restore verification.

## 6. Изменение схемы БД

Новая migration для V1.0.4 не требуется.

Migration head:

`0031_v1_0_0_idempotency_integrity`

## 7. Ограничения проверки

Не заявляются как выполненные:

- live production payment E2E с реальными credentials;
- live Remnawave production E2E;
- полный Vite production build без установленных frontend dependencies.

Это не заменяет staging/production acceptance test с реальными интеграциями.

## 8. Итог

Найденная критическая ошибка устранена. Регрессионные тесты подтверждают новый lock-order invariant. Выпущен `1.0.4-realise`.
