# Production Operations Runbook V43

## Перед запуском

- HTTPS работает.
- DNS корректен.
- Caddy единственный внешний вход.
- Backend/Admin/Mini App не имеют host port exposure.
- PostgreSQL и Redis healthy.
- Remnawave healthy.
- Backup создан и проверен.
- Staging E2E полностью пройден.
- Production Gate включается только после PASS.

## Платёжная авария

1. Отключить production payments.
2. Зафиксировать incident.
3. Проверить provider health.
4. Проверить webhook events и reconciliation.
5. Не создавать второй платёж вручную для timeout-запроса без проверки первого провайдера.
6. После исправления повторить E2E.

## Ошибка fulfillment

1. Проверить Job и ProvisioningOperation.
2. Не выдавать VPN вручную до проверки состояния платежа.
3. Повторить безопасную job/reconciliation процедуру.
4. Проверить Remnawave.

## Restore

1. Включить maintenance.
2. Создать защитный backup.
3. Проверить checksum.
4. Сначала выполнить isolated test-restore.
5. Только после успешной проверки выполнять production restore.
6. Проверить миграции и health.
7. Оставить maintenance включённым при любой неоднозначности.

## Rollback

Вернуться только на последний проверенный release. После rollback повторить health, diagnostics и staging E2E.
