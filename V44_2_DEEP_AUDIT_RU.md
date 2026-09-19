# V44.2 — повторный аудит

Дата: 2026-09-14

## Найденные проблемы

1. Регрессионный тест V44 проверял старую строку версии `44.0.0-enterprise`, хотя приложение уже было `44.1.0-enterprise`. Тест обновлён.
2. `scripts/build-release.sh` и VPS installer всё ещё содержали версию `44.0.0-enterprise` и старое имя релиза. Исправлено.
3. Release manifest содержал неверный `previous_migration_head` и старое имя detached manifest. Исправлено.
4. Регистрация устройств могла превысить `device_limit` при двух конкурентных запросах. Добавлен PostgreSQL advisory transaction lock на пользователя.
5. Конкурентный trial claim мог создать гонку между проверкой и вставкой. Добавлен PostgreSQL advisory transaction lock на пользователя; UNIQUE(user_id) остаётся финальным инвариантом.
6. Trial worker мог локально записать expiry назад после уже успешного удалённого продления. Теперь локальный expiry не уменьшается относительно удалённого значения.

## Проверки

- Pytest: **114 passed**.
- Python AST/compile: OK.
- Bash syntax для всех `.sh`: OK.
- Migration chain до `0022_enterprise_suite`: OK.
- ZIP integrity: проверяется при финальной сборке.
- Docker runtime / внешний платёжный sandbox E2E: не запускались, поскольку Docker daemon и реальные внешние sandbox credentials недоступны в текущей среде. Production payment gate остаётся fail-closed.

## Ограничения

Статический аудит не заменяет запуск полного production-like Docker stack и реального provider sandbox. Эти проверки должны выполняться на staging/VPS перед включением production payments.
