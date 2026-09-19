# Полная процедура Production E2E V43

## Цель

Доказать, что платёжная цепочка безопасна от создания заказа до refund.

## Preconditions

- sandbox credentials;
- отдельный staging Remnawave;
- отдельная staging DB/Redis;
- HTTPS;
- тестовый тариф;
- staging confirmed.

## Обязательные этапы

1. Health.
2. Создание тестового пользователя.
3. Создание sandbox payment.
4. Checkout.
5. Подписанный webhook.
6. Проверка provider status.
7. Проверка exact amount/currency.
8. Paid state.
9. Fulfillment job.
10. Remnawave provisioning/extension.
11. Повторный webhook.
12. Проверка отсутствия повторной выдачи.
13. Refund.
14. Проверка итогового состояния.
15. Cleanup.
16. Запись результата.

## PASS

PASS разрешён только когда каждый обязательный этап подтверждён. Простая строка `FULL_E2E_PASS`, добавленная вручную, не должна использоваться как доказательство.

## После PASS

Администратор с `security.manage` включает Production Gate. Если staging configuration изменена, gate автоматически сбрасывается.
