# Remnawave VPN Shop 44.5.4 Enterprise — глубокий аудит и исправления

Дата: 2026-09-14

## Результат

Проведён повторный аудит версии 44.5.3 с фокусом на платёжный контур, refunds/fulfillment, referral ledger, proxy-aware security, конкурентный доступ и release tooling.

Найдено и исправлено 4 дефекта.

### HIGH — refund reconciliation не отзывал доступ

В `refund_revoke_scheduler()` успешный внешний refund переводил Payment/RefundRequest в `refunded`, но не запускал безопасный revoke. В результате при успешном refund, обнаруженном фоновой reconciliation-процедурой, пользователь мог сохранить оплаченный VPN-доступ.

Исправление: после подтверждённого refund scheduler вызывает `_safe_revoke_for_refunded_payment()` и переводит запрос в `refunded_pending_revoke`, если Remnawave временно недоступен.

### HIGH — referral reward не отзывался при refund

Referral reward начислялся при fulfillment, но при последующем refund не выполнялся clawback. Это создавало финансовый дисбаланс.

Исправление: добавлен атомарный `_reverse_referral_reward_for_refund()`, работающий идемпотентно через `ReferralReward.status`. При необходимости отрицательный баланс отражает реальную задолженность после уже выполненного withdrawal.

### MEDIUM/HIGH — entitlement snapshot частично игнорировался при восстановлении существующего remote user

В ветке fulfillment, где Remnawave user уже существовал, целевая дата рассчитывалась через текущий `Plan.duration_days`, хотя оплаченная транзакция уже имела immutable snapshot.

Исправление: используется `duration_days_snapshot` через локальную переменную `duration_days`.

### MEDIUM — admin login rate-limit использовал адрес reverse proxy

Основной API уже нормализовал IP через `_client_ip()`, но отдельный limiter для `/api/admin/auth/login` использовал `request.client.host`. За Caddy это адрес proxy-контейнера, поэтому один внешний клиент мог потенциально влиять на лимит других администраторов.

Исправление: login limiter использует тот же доверенный proxy-normalized `_client_ip()`.

## Регрессионные тесты

Добавлен `tests/test_v45_4_deep_regressions.py`.

Проверяются:
- proxy-aware admin login rate limit;
- использование entitlement snapshot в existing-remote fulfillment;
- revoke при refund reconciliation;
- идемпотентный referral reward clawback;
- подключение reversal во всех завершённых refund paths.

## Проверки

- `pytest -q` — **138 passed**
- `python -m compileall -q backend` — **PASS**
- `bash -n install.sh deploy/*.sh scripts/*.sh` — **PASS**
- YAML parse для `docker-compose.yml` и `docker-compose.integration.yml` — **PASS**
- ZIP integrity — **PASS**

## Ограничения среды

Реальные production credentials платёжных систем, живой Remnawave API и Docker daemon в среде аудита недоступны. Поэтому внешний production E2E, реальный restore PostgreSQL и runtime container integration не выдаются за успешно выполненные проверки.

Frontend dependency installation/build также не был искусственно объявлен успешным: попытка подготовить npm lockfile завершилась timeout в sandbox. Это оставлено как отдельный release risk, а не скрыто под зелёным статусом.
