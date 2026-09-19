# V34 Production Release

## Исправления
- Разделены `support.read` и `support.write`; ответ на тикет больше не доступен роли только с `read`.
- Админский список тикетов защищён отдельным permission `support.read`.
- Monitoring Center больше не ищет heartbeat по неправильному ключу `worker_role`: состояние берётся из `WorkerState` по реальному `worker_id`, роли и свежести heartbeat.
- Добавлена диагностика количества здоровых worker-инстансов.
- Ошибки health lookup теперь логируются вместо полного подавления.
- `/api/me/traffic` повторно проверен: endpoint возвращает только Remnawave-данные текущей подписки; найденная ранее формулировка про утечку тикетов не подтверждается текущим исходником и не была внесена как изменение.

## Аудит
- Полный существующий regression suite расширен тестами RBAC и worker health.
- Статический AST/compile/bash/Compose/архивный аудит выполняется release builder.
- Production E2E с реальными PostgreSQL/Redis/Remnawave/payment provider по-прежнему требует внешнего окружения.
