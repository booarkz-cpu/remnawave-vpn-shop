# Remnawave VPN Shop 44.5.11 Enterprise — Very Deep Systems Audit

## Scope

Проведён повторный cross-system аудит версии 44.5.10: backend/API, PostgreSQL/Alembic, payment state machine, webhook deduplication, idempotency/recovery, fulfillment/trial worker, Remnawave integration, referrals/promos, authentication/MFA, backup/restore, Docker/release tooling.

Особый акцент — бизнес-инварианты, state transitions, TOCTOU/race conditions и внешние non-idempotent side effects. Такой подход соответствует рекомендациям OWASP по ручному secure code review и business-logic testing. 

## Найденные дефекты и исправления

### CRITICAL — webhook event claim использовал неправильный conflict target

Миграция `0027_v44_5_10_financial_integrity` создавала уникальность `(provider,event_id)`, но raw SQL использовал `ON CONFLICT (event_id)`. В PostgreSQL это не соответствует уникальному индексу и могло ломать обработку подтверждённых webhook.

Исправлено:

- `ON CONFLICT (provider,event_id)`;
- ORM-модель `PaymentProviderEvent` синхронизирована с DB invariant;
- добавлен regression test.

### HIGH — `creation_unknown` фактически выпадал из reconciliation

После неопределённого результата создания платежа запись переводилась в `creation_unknown`, но scheduler/admin reconciliation искали только `pending`/`paid`. В результате операция могла оставаться без автоматического восстановления.

Для YooKassa исправлено безопасно через повтор с тем же `order_id`, который является idempotency key provider API. Это не создаёт новый charge, а возвращает существующий результат provider operation.

`creation_unknown` теперь включён в background/admin reconciliation.

Для providers без подтверждённого provider-level idempotency create контракт повторное списание по-прежнему блокируется.

### HIGH — idempotent retry зависел от изменившегося promo state

До исправления перед поиском существующего Payment заново выполнялась promo validation. Если промокод после первого запроса истёк/отключён/исчерпал лимит, повтор того же Idempotency-Key мог получить ошибку вместо восстановления существующего payment intent.

Исправлено: durable Payment intent ищется раньше mutable promo validation; для существующей операции используются immutable payment snapshots.

### HIGH — Trial worker использовал актуальный Plan вместо Trial snapshot

При создании нового Remnawave user trial worker передавал `plan.traffic_limit_gb` и `plan.remnawave_profile_id`, хотя TrialGrant уже сохранял snapshot.

Также для существующего remote user entitlement не обновлялся.

Исправлено:

- новый user создаётся с Trial snapshot;
- существующий user получает `update_entitlements()` из Trial snapshot;
- изменение Plan после выдачи trial больше не меняет обещанные условия trial.

### MEDIUM — release tooling оставался на 44.5.10

Обновлены:

- `scripts/build-release.sh`;
- `deploy/install-vps.sh`;
- `release-manifest.template.json`;
- release consistency tests.

Новая версия: `44.5.11-enterprise`.

## Verification

- `pytest -q`: **187 passed**
- Python compileall: PASS
- AST parse всех backend Python files: PASS
- Bash syntax: PASS
- Docker Compose YAML parse: PASS
- Alembic graph: PASS; единственный head `0027_v44_5_10_financial_integrity`
- dangerous-pattern scan (`shell=True`, `verify=False`, `pickle.loads`, `yaml.load`, `os.system`): clean
- ZIP integrity: PASS
- release consistency: PASS

## Важное ограничение

В sandbox отсутствуют реальные production/staging credentials платёжных систем, live Remnawave API и production Docker runtime. Поэтому внешний E2E не объявляется пройденным. Локальные regression и static checks не заменяют проверку реальных внешних trust boundaries.
