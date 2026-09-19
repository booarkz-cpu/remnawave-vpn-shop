# V2.0.0-realise — глубокий продуктовый и критический аудит

Дата: 2026-09-14

## 1. Результат

Релиз `2.0.0-realise` объединяет продуктовые функции Enterprise-линейки и дополнительное критическое hardening-проверение.

Проверка выполнена по исходному коду текущего релиза, а не только по предыдущему отчёту. Основной фокус: state machines, TOCTOU, concurrent requests, transaction integrity, external side effects, authentication/session lifecycle, subscription lifecycle и recovery. OWASP прямо рекомендует для бизнес-логики моделировать серверные состояния, атомарно защищать check-then-act операции и отдельно тестировать concurrency. См. Secure Code Review и Business Logic Security Cheat Sheets.

## 2. Реализованные функции

### Billing / subscriptions
- Billing Center пользователя: история платежей и текущая подписка.
- Явный lifecycle подписки: `active`, `cancel_scheduled`, `grace`, `revoke_pending`, `expired`, `cancelled`.
- Scheduled cancellation и resume.
- Grace period после неуспешного auto-renew.
- Фоновый lifecycle worker с повторной попыткой remote revoke.
- Снимки коммерческих условий платежа сохраняются и не зависят от последующих изменений тарифа.

### Security Center
- Серверные user sessions с JTI.
- Revocation текущей сессии при logout.
- Revoke-all sessions.
- Проверка User-Agent и срока действия сессии.
- Список активных устройств и security events.

### Customer 360
Администратор получает агрегированную карточку пользователя:
- профиль;
- subscription lifecycle;
- платежи;
- refunds;
- устройства;
- referral ledger;
- support tickets;
- fraud signals.

### Anti-fraud / operations
- Risk summary endpoint с open/critical signals.
- Existing Fraud Center и feature-level monitoring сохранены.
- Jobs Center и retry workflow сохранены.
- System Health проверяет PostgreSQL, Redis и Remnawave.
- Incident mode и payment gate сохранены.

### Support
- Existing Support Center сохранён.
- Customer 360 связывает тикеты с платежами, подпиской, устройствами и fraud context.

### Dry Run
- Refund Dry Run показывает сумму, валюту, текущую подписку, наличие более поздних fulfilled payments, referral reward и планируемые side effects.
- Dry Run не изменяет БД.

### Gift system
- Администратор создаёт gift codes.
- Лимит использований и expiry.
- Уникальное использование одним аккаунтом.
- Remote provisioning/extension выполняется до окончательной активации.
- Используется operation key и сохранённые expected expiry значения для восстановления после потерянного ответа.

### Admin UI / Mini App
- Customer 360.
- Gift management.
- System Health.
- Billing Center данные в Mini App.
- Subscription lifecycle controls.
- Gift redemption.
- Security Center и revoke-all sessions.

## 3. Критические исправления, найденные при текущем аудите

### C-01 — удалённая подписка не должна оставаться активной после окончания grace/cancellation

Обнаружен риск рассинхронизации local subscription и Remnawave: локальный expiry сам по себе не отключает remote user.

Исправление:
1. lifecycle worker переводит запись в `revoke_pending`;
2. удерживает user lock и `FOR UPDATE`;
3. выполняет `RemnawaveClient.disable_user()`;
4. только после успешного remote side effect переводит состояние в `expired`/`cancelled`;
5. при ошибке оставляет `revoke_pending` для следующей попытки.

### C-02 — gift activation не является только локальным кредитом

Нельзя считать gift redeemed, если VPN entitlement не создан/продлён в Remnawave.

Исправление:
- durable `GiftRedemption`;
- operation key `gift:<gift_code>:<user>`;
- expected-before/after expiry;
- remote create/extend;
- reconciliation после потерянного ответа;
- `completed` выставляется только после успешного remote workflow.

### C-03 — user bearer token теперь имеет серверный session state

Ранее logout мог удалить cookie, но уже выданный bearer JWT оставался действительным до истечения срока.

Исправление:
- `user_sessions`;
- JTI hash;
- server-side revocation;
- logout revokes current session;
- revoke-all sessions;
- UA consistency check.

### C-04 — сохранены предыдущие финансовые lock invariants

Текущий код сохраняет единый порядок критических locks:

`user lock → payment lock → DB FOR UPDATE → external side effect`

Выполнены regression tests для fulfillment/refund/auto-renew и stale User/Payment snapshots.

## 4. Дополнительная проверка

Проверены:
- payment idempotency;
- provider webhooks;
- refund reconciliation;
- fulfillment retries;
- auto-renew;
- referral reversal;
- device limits;
- privacy deletion;
- Telegram/Yandex authentication;
- admin MFA/RBAC;
- request-body limits;
- archive traversal;
- SSRF/DNS pinning;
- backup/restore;
- Redis lock renewal;
- Alembic chain;
- release tooling;
- TSX syntax/transpilation.

## 5. Тесты

`267 passed`

Дополнительно:
- `python -m compileall -q backend` — PASS;
- `bash -n install.sh deploy/*.sh scripts/*.sh` — PASS;
- Docker Compose YAML parse — PASS;
- Admin TSX transpile — PASS;
- Mini App TSX transpile — PASS;
- ZIP integrity — PASS;
- SHA-256 verification — PASS.

## 6. Database

Migration head:

`0032_v2_0_0_product_features`

Migration добавляет:
- subscription lifecycle columns;
- `user_sessions`;
- `gift_codes`;
- `gift_redemptions` с operation state и idempotency metadata.

## 7. Ограничения проверки

Live production E2E с реальными платёжными credentials, Telegram Bot API и живым Remnawave не выполнялся в этой среде.

Полный Vite production build не заявляется без установленного `node_modules`; TS/TSX transpilation проверена.

Это означает, что release является source-level audited/reproducible build, а не заменой staging acceptance test.
