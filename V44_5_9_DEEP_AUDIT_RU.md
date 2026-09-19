# V44.5.9 Enterprise — Very Deep Audit

Дата аудита: 2026-09-14

## Область

Проверены backend/API, платежный контур, auto-renew, trial, fulfillment, Remnawave provisioning, webhook event state, referral/promo flows, device limits, admin security/session logic, migrations, release tooling, Docker Compose и shell scripts.

## Найденные и исправленные проблемы

### HIGH — Trial retry мог выдать повторный бесплатный срок

Trial worker вычислял новый target expiry при каждом retry. Если Remnawave успешно применил extension, но ответ/локальная транзакция потерялись, следующий retry видел уже увеличенный remote expiry и мог снова добавить полный trial period.

Исправление: TrialGrant получает `expected_before_expires_at` и `expected_after_expires_at`; target фиксируется до внешнего вызова и используется повторно. `extend_idempotent()` делает retry no-op, если target уже достигнут, и fail-closed при неожиданном изменении remote expiry.

### HIGH — Trial entitlement зависел от изменяемого Plan

После выдачи trial администратор мог изменить traffic/device/profile у Plan до выполнения worker job.

Исправление: TrialGrant сохраняет snapshots `traffic_limit_gb`, `device_limit`, `remnawave_profile_id`; worker использует их независимо от последующих изменений Plan.

### HIGH — Trial не применял entitlement к уже существующему Remnawave user

При существующем remote user trial продлевал срок, но мог оставить старый traffic/profile.

Исправление: перед trial extension вызывается `update_entitlements()` со snapshot значениями.

### HIGH — Revoked device можно было активировать сверх лимита

Проверка device limit выполнялась только при создании нового `UserDevice`. Повторная активация ранее revoked устройства обходила лимит.

Исправление: reactivation теперь также проверяет snapshot device limit под тем же per-user advisory lock.

### HIGH — Stale webhook event мог застрять навсегда

`PaymentProviderEvent` в состоянии `processing` после падения worker/webhook handler не мог быть повторно захвачен: reclaim разрешался только для `failed/retry`.

Исправление: `processing` event старше 10 минут может быть безопасно reclaimed, при этом обновляется `received_at`.

### HIGH — Auto-renew мог навсегда застрять на failed/pending payment

Scheduler искал только один фиксированный order id. После canceled/failed recurring payment следующий цикл видел старую запись и не создавал новую попытку.

Исправление: scheduler анализирует все попытки текущего renewal window, повторно проверяет pending payment через YooKassa, создает новый deterministic idempotency key только после подтвержденного failed/canceled состояния и никогда не создает второй charge при unresolved/paid attempt.

### HIGH — Auto-renew мог создать второй charge при неоднозначном результате предыдущей попытки

Если внешний charge был создан, но локальная проверка результата временно не сработала, новый scheduler цикл мог не видеть предыдущую попытку.

Исправление: поиск выполняется по всему prefix renewal order IDs; unresolved latest attempt блокирует новый charge до получения финального состояния.

## Проверки

- 175 тестов — PASS
- Python compile/AST — PASS
- Bash syntax — PASS
- Docker Compose YAML parse — PASS
- migration chain — PASS; head `0026_v44_5_9_retry_hardening`
- ZIP integrity — PASS
- release version consistency — PASS
- detached SHA-256 — PASS
- опасные шаблоны `shell=True`, `verify=False`, `pickle.loads`, небезопасный `yaml.load` — не обнаружены

## Ограничения

Live production/staging payment credentials, настоящий Remnawave API и production Docker runtime недоступны в sandbox. Поэтому внешний E2E не объявляется пройденным. Frontend `npm install` в sandbox превысил доступный timeout; backend и release verification полностью выполнены.

## Итог

Версия: **44.5.9-enterprise**.

Главный акцент релиза — устранение повторной выдачи entitlement при retry и устранение финансово опасной неопределенности auto-renew. State-machine и concurrency проверки выполнялись с учетом рекомендаций OWASP по business-logic security.
