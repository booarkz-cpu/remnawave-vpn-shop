# Remnawave VPN Shop 2.2.1 — Установка одной командой

## Что устанавливает скрипт

Текущая команда установки:

```bash
sudo bash install.sh
```

Скрипт автоматически:

1. Проверяет root и Debian/Ubuntu.
2. Устанавливает Docker Engine/Compose и системные зависимости.
3. Запрашивает только инфраструктурные и провайдерские данные, которые невозможно безопасно угадать.
4. Генерирует `APP_SECRET`, пароль PostgreSQL и другие runtime secrets.
5. Создаёт `.env` с правами `0600`; ручное редактирование не требуется.
6. Явно пишет `BACKUP_S3_ENABLED=true/false`, поэтому отключённый S3 не ломает Pydantic Settings.
7. Генерирует `package-lock.json` для Admin и Mini App с таймаутом, после чего Docker использует `npm ci`.
8. Получает immutable digest для build-stage Python/Node/Nginx и runtime Redis/PostgreSQL/Caddy.
9. Записывает pinned runtime images в `.env` и `.env.images`.
10. Настраивает UFW: только SSH, TCP 80/443 и UDP 443. PostgreSQL/Redis/backend наружу не публикуются.
11. Включает Fail2Ban для SSH и unattended security updates.
12. Проверяет SSH-конфигурацию перед reload.
13. Собирает backend, worker, bot, admin и Mini App.
14. Запускает PostgreSQL/Redis и выполняет health-check.
15. Применяет Alembic migrations.
16. Выводит URL панели, Mini App и API.

Если npm registry недоступен, установка завершается с понятной ошибкой вместо бесконечного ожидания.

## Возможности приложения

### Клиентская часть
- Авторизация Telegram WebApp.
- Опциональный Yandex ID.
- Каталог тарифов.
- Промокоды и акции.
- Создание платежей.
- История платежей.
- Личный кабинет VPN-подписки.
- Информация о трафике и квоте.
- Реферальная программа.
- Заявки на вывод реферального баланса.
- Тикеты поддержки.
- Экспорт и анонимизация данных аккаунта.
- Необязательное автопродление через YooKassa.

### Интеграция с Remnawave
- Provisioning нового пользователя.
- Продление существующей подписки.
- Проверка продления на стороне Remnawave с идемпотентностью.
- Получение subscription URL.
- Retry при временной недоступности.
- Предохранитель circuit breaker.
- Безопасный revoke после подтверждённого возврата.

### Платежи
- YooKassa.
- Platega.
- RollyPay.
- Idempotency для создания заказа.
- Webhook verification и deduplication.
- Проверка платежа у провайдера.
- Сверка платежей.
- Выполнение возврата.
- Сверка статуса возврата.
- Восстановление операций с ожидающим возвратом/отзывом.

### Административная панель
- RBAC.
- Optional 2FA/TOTP и recovery codes.
- Session management/revoke-all.
- Users, plans, payments.
- Content/Bot/Mini App.
- Marketing/promotions/broadcasts.
- Backup/restore.
- Security events.
- Recovery Center.
- Support.
- Refund Center.
- Worker Fleet.
- Release/update/rollback tools.
- Monitoring Center.
- Durable Job Queue.
- Anti-Fraud.
- Referral Payout Center.

### Надёжная очередь задач

Worker использует PostgreSQL row locking (`SKIP LOCKED`), lease timestamp и worker ID. Поддерживаются:

- queued/processing/completed/failed;
- attempts/max_attempts;
- bounded exponential retry;
- stale-job recovery после 10 минут;
- fulfillment jobs;
- audit/error information.

### Мониторинг и центр инцидентов
Отслеживаются:

- API metrics;
- worker heartbeat;
- queued/processing/failed jobs;
- disk usage;
- fulfillment failures;
- backup freshness;
- security incidents;
- payment/refund reconciliation.

### Антифрод
Базовые velocity-сигналы и ручная обработка сигналов через Admin. Система не блокирует легитимный платёж только по одному слабому сигналу.

### Резервное копирование и аварийное восстановление
- Local encrypted backups.
- S3-compatible off-site backups.
- Remote verification/retention.
- SHA-256 validation.
- Safe archive extraction.
- Pre-restore backup.
- MFA requirement for destructive restore when MFA is enabled.
- Fail-closed update/rollback recovery.

### Payouts
Referral withdrawals проходят отдельный lifecycle и RBAC. V42 поддерживает безопасный manual payout provider; автоматический payout требует отдельного API-адаптера конкретного платёжного сервиса и не имитируется изменением статуса.

## После установки

2FA не включается автоматически. Включить её можно в Admin → Безопасность.

Проверки:

```bash
cd /opt/vpn-shop
./scripts/preflight.sh
./scripts/security-scan.sh
./scripts/doctor.sh
```

Обновление:

```bash
./scripts/update.sh
```

Откат:

```bash
./scripts/rollback.sh
```

Перед реальными платежами необходимо выполнить staging E2E с PostgreSQL, Redis, Remnawave и sandbox выбранного платёжного провайдера.
