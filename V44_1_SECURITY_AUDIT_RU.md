# V44.1 — аудит безопасности и исправления

Дата: 2026-09-14

## Результат

После повторного полного статического аудита V44 были выявлены и исправлены три функционально-безопасностные проблемы:

1. **SSRF в Enterprise Monitoring** — проверка принимала любой HTTPS hostname без проверки разрешаемых IP. Добавлена проверка localhost, loopback, private, link-local, reserved, multicast и unspecified адресов; проверка выполняется и при фактическом scheduler-запросе.
2. **Лимит устройств не применялся** — API регистрации устройства позволял превысить `Plan.device_limit`. Теперь перед созданием нового устройства проверяется активная подписка и число активных устройств.
3. **Небезопасная повторная выдача Trial после сбоя БД** — при наличии уже созданного пользователя Remnawave worker мог повторно считать операцию новой. Теперь перед созданием/продлением проверяется удалённый expiry, и существующий пользователь доводится до ожидаемого срока.

## Автотесты

`113 passed`

Проверены:

- Python AST compilation всех `.py` файлов;
- Bash syntax всех scripts/deploy scripts;
- Docker Compose YAML parsing;
- Alembic migration chain, единственный head: `0022_enterprise_suite`;
- ZIP integrity;
- security regression tests;
- Enterprise V44 tests;
- legacy regression suite.

## Ограничения проверки

Docker daemon в среде аудита недоступен, поэтому настоящий `docker compose build/up` и внешний платёжный sandbox E2E выполнить невозможно. Production payment gate не объявляется пройденным на основании статического тестирования.
