# V44.5.17 Enterprise — очень глубокий аудит и исправления

Дата: 2026-09-14

## Исходная версия

Аудит выполнен поверх `44.5.15-enterprise` из переданного релизного ZIP.

## Методика

Проверены:

- финансовые workflow: checkout, idempotency, webhooks, fulfillment, auto-renew, refund/reconciliation;
- state-machine переходы и повторное выполнение операций;
- concurrency/TOCTOU для платежей, provisioning, withdrawals и privacy deletion;
- referral/promo/trial invariants;
- authentication, MFA, recovery codes, session lifecycle;
- account deletion и удалённый Remnawave entitlement;
- uploads/resource limits;
- SSRF/monitoring URL validation;
- ORM/DB constraints и Alembic chain;
- Docker/Compose, shell tooling и release reproducibility;
- regression tests и статический синтаксический контроль.

Основной принцип — проверять не только happy path, но и состояние после повторов, параллельных запросов, ошибок внешнего API и изменения данных между шагами workflow.

## Найденные дефекты V44.5.17

### CRITICAL — refund/fulfillment race

Обнаружено окно между началом fulfillment и окончательным применением статуса refund. Refund не использовал тот же distributed payment-side-effect lock, что fulfillment.

Сценарий:

1. webhook переводит payment в `paid`;
2. fulfillment начинает удалённое provisioning/extension;
3. одновременно admin/provider reconciliation завершает refund;
4. без общего lock fulfillment мог после refund записать `completed` и/или повторно выдать entitlement.

### Исправление

- введён единый `lock:fulfill:payment:<id>` для payment side effects;
- execute refund, refund reconciliation и fulfillment используют общий lock;
- fulfillment перед финальным commit заново блокирует Payment row и проверяет, что payment всё ещё `paid` и не terminal;
- refund больше не может одновременно завершать финансовую операцию и позволять старому fulfillment-коммиту пройти.

---

### CRITICAL — privacy deletion race с provisioning

Удаление аккаунта могло конкурировать с уже запущенным fulfillment, особенно если Subscription ещё не существовала: deletion мог завершиться, а worker затем создать удалённому пользователю новую VPN-подписку.

### Исправление

- введён user-level lock `lock:fulfill:user:<id>`;
- account deletion сериализуется с provisioning;
- fulfillment отказывается работать с `User.deleted_at != NULL`;
- удаление блокируется при конфликтующем provisioning;
- удалённые account tokens перестают быть валидными сразу после commit.

---

### HIGH — JWT пользователя оставался действительным после удаления аккаунта

До V44.5.17 пользовательский JWT мог оставаться действительным до истечения TTL даже после privacy deletion, потому что user token не имел persistent revocation marker.

Это позволяло после удаления продолжать обращаться к user API от имени уже удалённого аккаунта.

### Исправление

Добавлен `users.deleted_at` и проверка в `user_from_token()`.

После anonymization любой ранее выданный user JWT получает `401` независимо от оставшегося TTL.

---

### HIGH — удалённые устройства и recurring method оставались активными

Privacy deletion anonymized основную запись User, но lifecycle дочерних access objects был неполным.

### Исправление

При deletion:

- все `UserDevice` переводятся в `revoked`;
- `AutoRenewMethod` отключается;
- recurring method получает статус `deleted`;
- auto-renew пользователя выключается.

Финансовая история и referral ledger намеренно не удаляются: это бухгалтерские/аудитные данные, необходимые для reconciliation.

## Regression coverage

Добавлен `tests/test_v44_5_16_deep_regressions.py`:

- deleted users rejected by user token middleware;
- privacy deletion serialized against fulfillment;
- device revocation;
- deleted-user fulfillment rejection;
- shared refund/fulfillment payment lock;
- final fulfillment payment-state guard;
- migration 0030;
- release tooling consistency.

## Итоговые проверки

- **210 passed**
- Python AST — OK
- `compileall` — OK
- `bash -n` — OK
- Docker Compose YAML parse — OK
- Alembic: **30 revisions**, single head `0030_v44_5_16_privacy_and_refund_integrity`
- ZIP integrity — OK
- SHA-256 verified
- detached manifest соответствует ZIP
- `.env`, SHA256 и manifest не включены внутрь ZIP

## Release

Version: `44.5.17-enterprise`

Artifact:
`remnawave_vpn_shop_v44_5_16_enterprise_deep_audited_fixed.zip`

SHA-256:
`09bfcc04660e37b0f2670139922a09f7604c333bbefaf958c355aec867854686`

Migration head:
`0030_v44_5_16_privacy_and_refund_integrity`

Tests:
`210`

## Ограничения проверки

Реальные production/staging платежные credentials, живой Remnawave API и production PostgreSQL не предоставлены в среде аудита. Поэтому внешний E2E с реальным провайдером не объявляется пройденным.

Также Docker runtime и полноценный frontend production build требуют соответствующей runtime-инфраструктуры; в рамках исходного статического/release аудита проверены конфигурации, синтаксис и backend regression suite.

## Residual risk

DNS rebinding/TOCTOU для hostname-based monitoring остаётся архитектурным residual risk: URL проверяется через DNS перед запросом, но HTTP-клиент может выполнить новое DNS-разрешение. Полное устранение требует pinning/контролируемого resolver/transport уровня, а не только повторной проверки hostname.
