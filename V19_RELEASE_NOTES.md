# Remnawave VPN Shop V19 Production

V19 объединяет релизы V16–V19 в один production-релиз.

## V16 — Production Security & Reliability
- серверные admin sessions с JTI, IP, User-Agent, expiry и revoke;
- ревокация сессий после изменения пароля/роли/блокировки;
- granular permissions для keys, sessions, backups, analytics и payments;
- retry-очередь для неуспешной выдачи Remnawave с backoff;
- отдельные payment/fulfillment статусы;
- безопасная проверка MIME + magic bytes загрузок;
- строгая валидация скидок и Decimal-арифметика.

## V17 — Admin Pro
- аналитика выручки 24h/7d/30d;
- пользователи, активные подписки, pending payments и failed fulfillment;
- system health: disk/memory/backup lock;
- active admin sessions в панели;
- ручной retry fulfillment.

## V18 — Customer Pro
- профиль подписки;
- subscription URL + copy;
- referral code и статистика;
- применение referral code;
- настройки auto-renew readiness;
- уведомления об окончании подписки.

> Настоящее автоматическое списание реализуется только через recurring API конкретного платёжного провайдера. V19 не хранит данные банковских карт и не имитирует автоматическое списание.

## V19 — Automation / DR
- S3-compatible off-site backup (R2/B2/MinIO/S3);
- SHA-256 verification;
- encrypted backup;
- restore database из проверенного backup;
- backup configuration из панели;
- автоматический expiry notification;
- автоматический fulfillment retry;
- Docker resource limits;
- strict firewall: только SSH, TCP 80/443 и UDP 443;
- healthcheck после установки/build.

## Важное
Перед первым production-запуском обязательно:
1. настроить DNS;
2. задать сильный APP_SECRET;
3. включить MFA для всех admin;
4. настроить off-site S3 backup;
5. создать backup и выполнить Verify;
6. один раз проверить Restore на тестовой среде;
7. настроить webhook URL платёжного провайдера;
8. проверить Remnawave API token;
9. проверить `docker compose ps` и `/health`.
