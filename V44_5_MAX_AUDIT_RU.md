# V44.5 Enterprise — максимальный аудит

Дата: 2026-09-14

## Исправления этого прохода

1. **Production payment gate для Auto-Renew**
   - Автопродление является реальной операцией списания.
   - Теперь scheduler не выполняет recurring charge, если глобальный `payments` выключен или `payments.production_gate != 1`.
   - Это предотвращает обход staging-gate через автоматическое продление.

2. **Инициализация PaymentProviderHealth**
   - На чистой БД таблица provider health пуста до первого открытия админского раздела feature flags.
   - Из-за этого обычный checkout мог ошибочно получить `Нет доступных платёжных провайдеров`.
   - Provider records теперь лениво bootstrap-ятся непосредственно в payment routing.

3. **Release tooling consistency**
   - Build script, manifest, installer и application version синхронизированы на `44.5.0-enterprise`.
   - Исправлено старое имя V44.3 artifact в build script.
   - Исправлено старое имя detached manifest.
   - Regression test теперь проверяет актуальный release contract.

## Проверки

- pytest: **118 passed**
- Python compileall: OK
- Bash syntax (`bash -n`): OK
- Docker Compose YAML parse: OK
- Alembic chain: `0022_enterprise_suite` — OK
- ZIP integrity: OK после сборки
- Payment gate regression: OK
- Auto-renew gate regression: OK
- Provider bootstrap regression: OK
- Device-limit concurrency regression: OK
- Trial concurrency regression: OK
- Idempotency regression: OK
- Remnawave expiry monotonicity regression: OK
- SSRF validation regression: OK

## Ограничения

Docker daemon и реальные sandbox credentials внешних платёжных провайдеров недоступны в среде аудита. Поэтому production provider E2E не объявляется пройденным. Production payment gate должен включаться только после реального staging E2E.
