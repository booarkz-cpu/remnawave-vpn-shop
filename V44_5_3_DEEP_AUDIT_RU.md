# Remnawave VPN Shop 44.5.3 Enterprise — глубокий аудит и исправления

Дата аудита: 2026-09-14

## Итог

Проведён повторный аудит версии 44.5.2 с независимой проверкой backend, платежей, возвратов, referral ledger, планов, backup/restore, reverse-proxy IP handling, concurrency и release tooling.

Результат: исправлены обнаруженные обычные, важные и критические по последствиям дефекты, добавлены regression checks.

## Исправленные дефекты

### CRITICAL / финансовые

1. **Refund reconciliation не отзывал VPN-доступ.**
   Если возврат подтверждался позднее через reconcile, платёж переводился в `refunded`, но подписка могла оставаться активной. Теперь reconciliation использует тот же безопасный revoke-контур, что и прямой refund.

2. **Повторный retry-revoke мог отозвать доступ после более новой покупки.**
   Общий helper теперь повторно проверяет наличие более позднего успешно исполненного платежа непосредственно перед revoke.

3. **Referral balance мог терять начисления при конкурентных выплатах.**
   Замена ORM read-modify-write на атомарный SQL increment устраняет lost update для одного реферера при параллельных fulfillment.

4. **Оплата могла получить изменённые после checkout коммерческие условия тарифа.**
   Payment теперь сохраняет snapshot duration/traffic/device/profile на момент создания. Fulfillment использует snapshot, а не текущую изменённую запись Plan.

### HIGH / важные

5. **Refund execution имел race между двумя администраторами.**
   Состояние возврата теперь сначала атомарно захватывается как `processing` и фиксируется отдельной транзакцией до внешнего API-вызова. Повторный запрос не создаёт второй refund.

6. **Revoke после refund вынесен в единый безопасный контур.**
   Это устраняет расхождение поведения между execute/reconcile/retry.

7. **Legacy referral withdrawal endpoints расходились с новым payout-контуром.**
   Legacy approve/paid теперь создают/используют `PayoutTransaction` так же, как новый ops API. Добавлены row locks.

8. **Concurrent approve/reject withdrawal мог привести к неконсистентному состоянию.**
   Withdrawal row теперь блокируется `FOR UPDATE` перед state transition.

9. **Backup/restore и isolated test-restore использовали hardcoded PostgreSQL host/user/database.**
   Все CLI операции получают параметры из `DATABASE_URL`.

10. **YooKassa IP allowlist за reverse proxy мог видеть IP Caddy вместо IP провайдера.**
    Caddy теперь явно перезаписывает `X-Forwarded-For` фактическим peer IP, а backend использует первый корректный адрес forwarded chain.

11. **Удаление используемого Plan могло сломать будущий fulfillment старых платежей.**
    Удаление теперь запрещено, если тариф используется платежами, подписками или trial grants; для такого тарифа следует использовать disable.

## Regression verification

- `pytest`: **134 passed**
- Python `compileall`: PASS
- `bash -n install.sh deploy/*.sh scripts/*.sh`: PASS
- миграционная цепочка: `0023_v44_5_3_billing_snapshots` → `0022_enterprise_suite`

## Ограничения среды

Не выполнялись реальные production payment API calls, живой Remnawave API и Docker runtime: соответствующие credentials/runtime отсутствуют в sandbox. Frontend `npm` installation/build не завершён в sandbox из-за ограничения внешнего доступа/времени; исходный frontend остаётся без изменений по runtime-коду.

Production payment gate по-прежнему требует успешного staging E2E.
