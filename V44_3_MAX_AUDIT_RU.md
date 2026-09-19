# V44.3 — максимальный повторный аудит

Дата: 2026-09-14

## Результат

- Pytest: **114 passed**
- Python compileall: PASS
- Bash syntax (`scripts/*.sh`, `deploy/*.sh`): PASS
- Docker Compose YAML parse: PASS
- ZIP integrity: PASS
- Migration chain: PASS (head 0022_enterprise_suite)

## Дополнительно найденные и исправленные проблемы

### 1. Восстановление существующего Remnawave-пользователя могло уменьшить срок
При восстановлении после потерянного ответа API локальная логика брала `now + duration`, не учитывая более длинный срок, уже существующий удалённо. Это могло привести к рассинхронизации и фактическому откату локального срока.

Исправлено: удалённый expiry читается перед восстановлением; целевой срок вычисляется как максимум текущего ожидаемого и удалённого срока. После операции срок перечитывается из Remnawave.

### 2. Аналогичный сценарий в Trial worker
Trial worker также должен был сохранять уже существующий более длинный удалённый срок.

Исправлено: target expiry не может быть меньше remote expiry.

### 3. Несогласованность версии release tooling
Активный код V44.2 содержал внутреннюю версию `44.1.0-enterprise` в API/build/install/manifest/test metadata.

Исправлено: единая версия `44.3.0-enterprise`.

## Проверенные зоны

- аутентификация пользователей и администраторов;
- MFA/session timeout/UA binding;
- CSRF;
- TrustedHost/CORS/security headers;
- rate limits;
- платежный production gate;
- provider routing/circuit breaker;
- idempotency;
- webhook/reconciliation/fulfillment;
- referral ledger;
- auto-renew;
- device limit и конкурентная регистрация;
- trial и конкурентная активация;
- monitoring SSRF/DNS private-address blocking;
- backup checksum/tar safety/isolated restore;
- SSH provisioning;
- admin content/media;
- campaign/rules/monitoring APIs;
- migration chain;
- release scripts and metadata.

## Ограничение

Docker daemon и реальные внешние sandbox-учётные данные платёжных провайдеров недоступны в текущей среде. Поэтому runtime Docker и полный внешний checkout → webhook → fulfillment → duplicate webhook → refund E2E не объявляются пройденными. Production payment gate должен оставаться закрытым до реального staging E2E.
