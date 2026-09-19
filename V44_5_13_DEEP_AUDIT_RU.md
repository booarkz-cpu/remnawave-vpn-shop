# Remnawave VPN Shop — V44.5.13 Enterprise Deep Audit

Дата аудита: 2026-09-14

## Итог

Проект прошёл повторный baseline-аудит после V44.5.12. Проверены backend, worker, платежные state-machines, webhooks, refund/withdrawal/referral flows, trial, Remnawave provisioning, authentication/MFA/CSRF/RBAC, uploads, backups/restore, SSRF-sensitive monitoring, Docker/Compose, Alembic chain, release tooling и dependency pinning.

### Найденные и исправленные дефекты V44.5.13

1. **ВАЖНЫЙ — idempotent checkout мог стать невосстановимым после изменения тарифа.**
   `POST /api/payments/create` проверял `Plan.enabled` до поиска уже существующего Payment по `Idempotency-Key`. Если оператор отключал тариф после создания durable intent, повтор запроса с тем же ключом возвращал 404 вместо восстановления исходной операции. Исправлено: существующий Payment разрешается первым; для уже созданного intent используются его immutable snapshots.

2. **ВАЖНЫЙ — внешний payment provider мог вернуть успешный HTTP-ответ без payment ID.**
   Код мог сохранить такой intent как `pending` с пустым `provider_payment_id`, оставляя состояние, которое невозможно надёжно сверить обычным provider-ID lookup. Исправлено: отсутствие внешнего payment ID теперь считается неопределённым результатом и переводит операцию в безопасный reconciliation path; повторное списание не выполняется автоматически.

3. **ВЫСОКИЙ — устаревшая cryptography dependency.**
   Проект использовал `cryptography==46.0.4`. На текущую дату для cryptography опубликованы security advisories, затрагивающие версии до 48.0.1, а отдельная проблема с PKCS#7 исправлена только в 50.0.0. Проект использует библиотеку для AES-GCM и encrypted secrets, поэтому dependency обновлена до `cryptography==50.0.1`. Источники: GHSA-537c-gmf6-5ccf и GHSA-g6cj-pr64-35w5. 

## Уже присутствующие защиты, подтверждённые аудитом

- Durable payment intents создаются до внешнего платежного вызова.
- Idempotency-Key используется для checkout.
- Unknown payment creation не приводит к blind fallback на другой provider.
- YooKassa unknown creation может быть безопасно повторена с тем же order ID.
- Webhook может привязать durable intent по immutable order ID.
- Provider webhook дополнительно проверяет provider-side status, amount и currency.
- Provider event idempotency использует `(provider,event_id)`.
- Refund state transition защищён row lock и отдельным processing state.
- Refund reconciliation не отзывает подписку, если есть более новый успешно fulfilled payment.
- Referral reward reversal выполняется один раз.
- Promo usage резервируется транзакционно с row lock.
- Trial claim сериализован PostgreSQL advisory lock и блокируется при действующей подписке.
- Subscription/Payment/Trial используют entitlement snapshots.
- Remnawave retry использует persisted expected-before/expected-after.
- Повторное provisioning существующего remote user переиспользует username/id и восстанавливает entitlement.
- Старый traffic/profile очищается при переходе на unlimited/no-profile entitlement.
- Admin RBAC, MFA, registered admin sessions и CSRF middleware присутствуют.
- Backup restore использует отдельную временную БД и проверку результата.
- Uploaded images имеют size limit и magic-signature validation.
- Monitoring URLs ограничены HTTPS и проверяются на private/local IP при конфигурации и перед запросом.
- Production payments gate требует свежий полный staging E2E.

## Проверки

- `pytest -q`: **197 passed**
- `python -m compileall -q backend`: **OK**
- `bash -n install.sh deploy/*.sh scripts/*.sh`: **OK**
- Alembic graph: **28 migration revisions, linear chain, head 0028_v44_5_12_logic_integrity**
- Docker Compose syntax: инструмент Docker отсутствует в текущей среде, поэтому runtime `docker compose config` здесь не выполнялся.
- Frontend builds: `node_modules` отсутствуют, поэтому Vite production builds не выполнялись.
- Production E2E: реальные provider credentials, PostgreSQL production instance и Remnawave production API отсутствуют, поэтому external payment/fulfillment E2E не заявляется как пройденный.

## Остаточные риски

1. Monitoring hostname имеет классический DNS TOCTOU residual risk: hostname проверяется на public resolution, затем HTTP client самостоятельно выполняет новое DNS resolution. Полное устранение требует DNS pinning/custom transport либо разрешения только literal IP.
2. Dependency scanners `pip-audit`, `trivy`, `syft` и npm audit не были доступны/полностью применимы в этой среде; dependency review дополнительно выполнен по актуальным security advisories.
3. Для полноценного release acceptance требуется staging E2E: checkout → webhook → fulfillment → duplicate webhook → refund → revoke/reconciliation.

## Методика

Аудит ориентирован на OWASP Secure Code Review: architecture, entry points, authentication/authorization, data flow, business logic, crypto, error handling и deployment configuration. Особое внимание уделено workflow state machines, concurrency, transaction atomicity и idempotency.
