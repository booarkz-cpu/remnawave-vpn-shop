# Remnawave VPN Shop V44 — полная документация

## 1. Назначение

V44 — production-oriented магазин VPN поверх Remnawave с Telegram Mini App, Telegram-ботом, административной панелью и PostgreSQL/Redis.

Релиз объединяет предыдущую production-безопасность V43.1 с Enterprise-набором функций:

1. 24/7 мониторинг;
2. Smart Payment Router;
3. антифрод;
4. личный кабинет;
5. управление устройствами;
6. автопродление;
7. конструктор Telegram-бота;
8. конструктор сообщений;
9. визуальный Mini App Builder;
10. тарифы 2.0;
11. Trial;
12. Campaign Manager;
13. расширенная аналитика;
14. Node Manager;
15. Rules Engine;
16. Support Center;
17. Disaster Recovery Mode;
18. staging E2E gate перед реальными платежами.

## 2. Архитектура

Сервисы Compose:

- `caddy` — единственная внешняя HTTP/HTTPS точка входа;
- `backend` — FastAPI API;
- `worker` — durable jobs, выдача VPN, retry, heartbeat, backup и monitoring;
- `bot` — Telegram Bot API/aiogram;
- `admin` — административная SPA;
- `miniapp` — Telegram Mini App;
- `db` — PostgreSQL;
- `redis` — rate-limit, locks и быстрые состояния.

Backend и UI не должны публиковать PostgreSQL/Redis напрямую наружу.

## 3. Новые V44 сущности

### UserDevice
Устройство пользователя. Имеет уникальный `device_key`, имя, платформу, последний IP/heartbeat и статус `active/revoked`.

### TrialGrant
Одноразовый trial на пользователя. Выдача создаёт durable job `trial:<id>`, после чего worker безопасно создаёт/продлевает пользователя Remnawave.

### Campaign
Кампания для broadcast/winback/retention/promotion. Содержит аудиторию и JSON-контент. Кампании создаются в статусе draft и могут быть переведены в scheduled/running/paused/completed.

### AutomationRule
Декларативное правило: событие + JSON-условия + JSON-действия. Произвольный Python/SQL код через UI не исполняется.

### MonitoringCheck
HTTPS health-check с интервалом, timeout, статусом, latency и failure streak. URL проходит `validate_public_url`, чтобы не превращать мониторинг в SSRF-прокси.

## 4. API V44

### Пользователь

`GET /api/me/devices` — список устройств.

`POST /api/me/devices` — зарегистрировать/обновить устройство.

`POST /api/me/devices/{id}/revoke` — отозвать устройство.

`POST /api/me/trial` — получить trial. Повторное получение запрещено уникальным ограничением `user_id`.

### Администратор

`GET /api/admin/enterprise/summary` — сводка Enterprise-функций.

`GET/POST /api/admin/enterprise/monitoring` — просмотр/добавление health-check.

`DELETE /api/admin/enterprise/monitoring/{id}` — удалить health-check.

`GET/POST/PUT /api/admin/enterprise/campaigns` — Campaign Manager.

`GET/POST/PUT /api/admin/enterprise/rules` — Rules Engine.

Все admin mutation endpoints проходят cookie-auth + CSRF + RBAC + rate limiting.

## 5. Smart Payment Router

Роутер учитывает:

- включён ли провайдер;
- priority;
- circuit breaker;
- накопленную статистику ошибок/успехов.

Критически важно: V44 не делает небезопасный автоматический fallback после неоднозначной ошибки создания платежа. Если внешний API мог создать платёж, повторная отправка в другой provider способна создать двойное списание. В такой ситуации транзакция должна быть разрешена reconciliation-процессом.

Это осознанная гарантия безопасности, а не ограничение производительности.

## 6. Антифрод

В проекте сохраняются FraudSignal и административный сканер. Рекомендуемые сигналы:

- высокая частота платежей;
- серия ошибок fulfillment;
- подозрительная комбинация аккаунтов/IP;
- массовая регистрация;
- повторное использование device fingerprint.

Автоматическое блокирование денег/аккаунта должно оставаться fail-safe: сначала сигнал, затем операторское решение или отдельно протестированное правило.

## 7. Monitoring

Worker каждые ~15 секунд проверяет due checks. Каждый check сам ограничивает частоту по `interval_seconds`.

Статусы:

- `ok` — HTTP 2xx/3xx;
- `degraded` — HTTP неуспешный;
- `down` — сетевой/timeout exception.

Failure streak фиксируется. Для streak 1/3/5 создаётся audit event.

## 8. Trial

Trial не считается оплаченной транзакцией и не проходит payment gate.

Порядок:

1. пользователь авторизуется;
2. API проверяет уникальный trial;
3. проверяет активный тариф;
4. создаёт `TrialGrant`;
5. создаёт durable `Job`;
6. worker создаёт/продлевает Remnawave;
7. статус trial становится `completed`.

При сбое worker использует retry/backoff. Максимум — 5 попыток для trial job.

## 9. Rules Engine

Правила хранятся как данные. Пример:

```json
{
  "event": "subscription.expiring",
  "conditions": {"days_left": 2},
  "actions": {"type": "notify", "template": "renewal_2d"}
}
```

UI не принимает исполняемый код. Реальный исполнитель правил должен иметь белый список событий и действий. Это предотвращает превращение Rules Engine в удалённое выполнение кода.

## 10. Campaign Manager и конструкторы

Предыдущий CMS уже поддерживает:

- меню Telegram-бота;
- start image;
- Mini App title/subtitle/background/image;
- кнопки Mini App;
- инструкции;
- дополнительные поля;
- рекламные блоки;
- промокоды;
- акции;
- broadcast.

V44 добавляет единый Campaign Manager для управления жизненным циклом кампаний. Перед production-рассылкой рекомендуется тестовая аудитория и ограничение rate.

## 11. Node Manager

Node Manager использует существующий Remnawave API и SSH provisioning. Перед удалённым provisioning проверяются compose/config и политика host key. Shell arguments передаются без небезопасной конкатенации.

## 12. Support Center

SupportTicket остаётся основным источником истины. Ответы администратора проходят RBAC и audit logging.

## 13. Disaster Recovery

Существующий V43 recovery flow включает:

- maintenance lock;
- pre-restore backup;
- checksum;
- tar safety validation;
- MFA для опасных операций при включённой MFA;
- migration;
- health-check;
- fail-closed после ошибки восстановления;
- isolated test-restore backup в отдельную PostgreSQL БД.

## 14. Безопасность

Обязательные механизмы:

- HttpOnly auth cookies;
- CSRF для cookie-auth mutation;
- TrustedHost;
- CORS allowlist;
- security headers;
- request size limit;
- Redis rate limiting;
- admin idle/absolute session timeout;
- User-Agent binding admin session;
- MFA/TOTP;
- recovery codes;
- encrypted secrets;
- audit log;
- idempotency key платежей;
- provider amount/currency verification;
- webhook deduplication;
- fulfillment locks;
- durable jobs;
- stale job recovery;
- circuit breaker;
- staging gate перед production payment creation.

## 15. Production payment gate

Реальные платежи разрешены только при:

- maintenance mode = off;
- feature `payments` = on;
- staging status = `passed`;
- `full_e2e=true`;
- успешная проверка не старше 24 часов.

Текущий staging runner специально не подделывает `FULL_E2E_PASS`: если checkout/webhook/fulfillment/refund не были реально проверены, production gate не снимается.

## 16. Миграции

Новый head:

`0022_enterprise_suite`

Перед запуском production:

```bash
alembic upgrade head
```

Downgrade 0022 удаляет только V44-таблицы.

## 17. Тестирование

Автоматический regression suite V44: **112 passed**.

Проверяются:

- предыдущие security/reliability contracts;
- migration chain;
- новые модели;
- новые API routes;
- worker trial job;
- admin UI contract;
- SSRF-safe monitoring URL validation;
- отсутствие произвольного subprocess execution в Rules Engine.

Ограничение среды: Docker CLI/daemon недоступен в текущей среде, поэтому фактический `docker build` и полный runtime Compose/E2E с внешними платёжными sandbox аккаунтами не могут быть честно заявлены как выполненные.

## 18. Проверка релиза

```bash
sha256sum -c remnawave_vpn_shop_v44_enterprise.sha256
unzip -t remnawave_vpn_shop_v44_enterprise.zip
```

Detached manifest содержит version, SHA256, migration head и число тестов.

## 19. Операционный порядок

1. Сделать backup.
2. Выполнить `alembic upgrade head`.
3. Проверить `/health`.
4. Проверить Redis/PostgreSQL.
5. Проверить Remnawave.
6. Проверить monitoring checks.
7. Выполнить staging E2E.
8. Проверить payment reconciliation.
9. Только после `FULL_E2E_PASS` открыть production payment gate.
10. Наблюдать worker heartbeat, fulfillment failures и provider health.

## 20. Что сознательно не заявляется

- Passkeys/WebAuthn пока не являются полноценным cryptographic login flow — есть защищённый inventory credential-ов.
- Staging E2E не объявляется полным, пока внешний sandbox checkout → webhook → paid → fulfillment → refund реально не пройден.
- Автоматический fallback после ambiguous payment error не включается.
- Docker runtime в этой среде не был запущен.

Эти ограничения оставлены fail-closed, чтобы документация не обещала больше, чем реально проверено.
