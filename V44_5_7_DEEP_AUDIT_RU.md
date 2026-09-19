# V44.5.7 — Very Deep Audit / Fixed

## Результат

Проведён повторный аудит поверх V44.5.6 с упором на бизнес-логику денег и доступа, конкурентные операции, идемпотентность, state transitions, retry/reconciliation и доверенные границы.

### Найдено и исправлено

1. **HIGH — отключённый администратором payment provider мог самовключиться.**
   После успешного создания платежа код устанавливал `PaymentProviderHealth.enabled=True`. Теперь успешный запрос только сбрасывает circuit breaker/ошибки; явный `enabled` меняется только административной операцией.

2. **HIGH — referral attribution можно было получить после создания pending payment.**
   Пользователь мог сначала создать платёж, затем установить referral и получить reward после webhook/fulfillment. В Payment добавлен immutable `referrer_id_snapshot`; fulfillment использует только snapshot.

3. **HIGH — промокод с лимитом мог быть использован несколькими одновременно созданными checkout.**
   Простая проверка `used_count` происходила до внешнего payment create и не резервировала слот. Добавлены атомарные `PromoReservation` и `reserved_count`; reservation создаётся под row lock, переносится в `consumed` при fulfillment и освобождается после истечения срока или неуспешного создания платежа.

4. **HIGH — refund старого платежа мог пропустить revoke из-за более нового платежа, который был только `paid`, но реально не выдан пользователю.**
   Защитой теперь считается только более новый payment с `fulfillment_status == completed`.

5. **MEDIUM/HIGH — продление существующей подписки мог начинаться от устаревшей локальной даты или от даты в прошлом.**
   Для entitlement теперь используется максимум из локального expiry, удалённого Remnawave expiry и текущего времени.

6. **MEDIUM — trial для существующего Subscription мог продлить отключённого Remnawave user, не включив его обратно.**
   Trial worker теперь проверяет remote status и выполняет `enable_user` перед extension.

7. **MEDIUM — два одновременных запроса установки referral могли гоняться.**
   Attribution теперь сериализуется `FOR UPDATE` на User row.

## Изменения схемы

Новая миграция:

`0024_v44_5_7_logic_hardening`

Добавляет:
- `payments.referrer_id_snapshot`;
- `promo_codes.reserved_count`;
- таблицу `promo_reservations` с уникальными `order_id` и `payment_id`.

## Проверки

- **157 тестов — passed**
- Python `compileall` — PASS
- AST parsing изменённых Python-файлов — PASS
- Bash syntax — PASS
- Docker Compose YAML — PASS
- статическая проверка отсутствия `health.enabled=True` — PASS
- проверка отсутствия старых hardcoded PostgreSQL CLI credentials — PASS

## Ограничения

В среде аудита отсутствуют реальные production/staging credentials платёжных провайдеров, живой Remnawave API и production Docker runtime. Поэтому внешний E2E не объявляется пройденным. Локальные regression/business-logic проверки выполнены на финальном состоянии исходников.

## Методика

Основной фокус: server-side derivation of security-relevant values, explicit workflow state, atomic check-and-act, external-operation idempotency, concurrency и abuse cases — в соответствии с рекомендациями OWASP по business-logic и secure code review.
