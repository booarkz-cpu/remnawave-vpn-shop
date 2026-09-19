# Remnawave VPN Shop 44.5.18 Enterprise — очень глубокий аудит и исправления

## 1. Объём

Проведён повторный baseline-аудит релиза V44.5.17 по всему репозиторию: backend/API, PostgreSQL/Alembic, платежные state machines и webhooks, refunds/reconciliation, auto-renew, referral/withdrawal ledger, fulfillment/provisioning, Remnawave integration, authentication/MFA/CSRF/RBAC, privacy deletion, uploads, SSRF-sensitive monitoring, backup/restore, Docker/Compose, release tooling и зависимости.

Основной критерий — не только наличие локальных проверок, но и сохранение бизнес-инвариантов при повторе, переупорядочивании и конкурентном выполнении операций. OWASP рекомендует для baseline review отдельно проверять state management, race conditions, transaction integrity, resource limits, authorization и workflow bypass; для денежных операций — idempotency и атомарность check-then-act.

## 2. Найденные дефекты V44.5.18

### CRITICAL — поздний успешный webhook мог воскресить уже возвращённый платёж

Все три webhook entry points раньше допускали переход `Payment.status != paid -> paid`. Для уже возвращённого платежа это создавало опасный переход:

`refunded -> paid -> fulfillment`

что потенциально позволяло повторно выдать VPN entitlement после refund.

### Исправление

- `refunded` и `refunded_pending_revoke` теперь являются terminal financial states для webhook fulfillment.
- Поздний `payment.succeeded` подтверждается, но игнорируется без повторного provisioning.
- Добавлены regression checks для YooKassa, Platega и RollyPay.
- Admin payment retry также отклоняет refunded payments.

### CRITICAL — YooKassa webhook мог привязать provider payment ID к неверному durable intent

YooKassa webhook не имел обязательной проверки `metadata.order_id` и привязывал неизвестный provider ID до проверки самого provider object. При наличии известного успешного YooKassa payment ID с совпадающими amount/currency это создавало риск cross-order binding.

### Исправление

Порядок теперь строго такой:

1. найти durable Payment по provider ID или immutable order ID;
2. проверить order mismatch;
3. запросить provider object напрямую;
4. проверить status + amount + currency + immutable order ID;
5. только после этого bind provider payment ID;
6. зарегистрировать webhook event;
7. изменить локальное состояние.

Для Platega/RollyPay аналогично добавлена проверка immutable order ID в provider API response.

### HIGH — auto-renew payment transition не использовал общий payment side-effect lock

Auto-renew мог подтвердить payment как `paid` одновременно с refund workflow. Fulfillment имел собственный lock, но переход состояния payment происходил до него. Это оставляло race window между `paid` и `refunded`.

### Исправление

Auto-renew теперь использует тот же distributed payment side-effect lock перед переходом `pending -> paid`, проверяет terminal refund states и только после этого запускает fulfillment.

### MEDIUM — release tooling зависел от PyYAML, но PyYAML не входил в runtime/build requirements

`scripts/build-release.sh` импортирует `yaml`, однако пакет не был зафиксирован в `backend/requirements.txt`. Это делало release build зависимым от случайно установленного пакета на машине оператора.

### Исправление

Добавлен `PyYAML==6.0.3`. На момент аудита это актуальный стабильный релиз PyYAML; upstream release 6.0.3 добавляет поддержку Python 3.14/free-threading. citeturn1search0turn1search2

## 3. Повторно проверенные инварианты

- durable payment intent создаётся до внешнего charge;
- idempotency key защищает повтор checkout;
- provider ID не меняется после binding;
- webhook provider/event deduplication scoped by provider;
- refund и fulfillment используют общий payment side-effect lock;
- refund reconciliation и retry-revoke используют тот же lock;
- user deletion сериализован с fulfillment;
- deleted users немедленно блокируются JWT lookup;
- active subscription блокирует trial;
- promo reservations атомарно учитывают `used_count + reserved_count`;
- referral withdrawal списывает баланс условным SQL UPDATE;
- approved/processing payout нельзя отменить обычным reject;
- remote entitlement обновляется вместе с quota/profile;
- `None` entitlement явно очищает старые remote quota/profile значения;
- provisioning retry использует persisted expected-before/expected-after;
- backup archive traversal проверяется до extraction;
- uploads имеют bounded reads;
- admin CSRF/session/RBAC проверки сохраняются;
- migration chain имеет один head.

## 4. Проверки релиза

- Pytest: **220 passed**
- Python compileall: **OK**
- Shell syntax: **OK**
- Docker Compose YAML parse: **OK**
- Alembic revisions: **30**
- Alembic single head: `0030_v44_5_16_privacy_and_refund_integrity`
- ZIP integrity: **OK**
- SHA-256 verification: **OK**
- final manifest matches artifact SHA: **OK**
- final SHA/manifest/.env files excluded from ZIP as intended
- stale `44.5.17` release markers removed from active source/release tooling

## 5. Ограничения проверки

Production E2E с реальными YooKassa/Platega/RollyPay credentials и live Remnawave API не выполнялся и поэтому не заявляется как пройденный. В окружении аудита отсутствуют Docker daemon и frontend `node_modules`, поэтому полноценный container runtime и Vite production build здесь не выдаются за подтверждённые.

Hostname-based monitoring по-прежнему требует отдельной инфраструктурной DNS pinning/transport защиты для устранения полноценного DNS-rebinding TOCTOU; текущая валидация отбрасывает localhost/private/link-local/reserved targets и отключает redirects, но это не эквивалент pinned resolver.

## 6. Релиз

Версия: **44.5.18-enterprise**

Artifact: `remnawave_vpn_shop_v44_5_18_enterprise_deep_audited_fixed.zip`

SHA-256: указан в detached release manifest и `.sha256` рядом с ZIP; проверяется против полного содержимого артефакта.

Migration head: `0030_v44_5_16_privacy_and_refund_integrity`

Tests: **220**
