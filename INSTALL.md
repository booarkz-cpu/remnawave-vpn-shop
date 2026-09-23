# Remnawave VPN Shop 3.1.6 — Установка одной командой

Версия **3.1.6** не меняет схему базы и не заменяет APK. Админка, Mini App и кабинет отвечают на HTTP: nginx пишет pid и кэш в `/tmp/nginx`, а Caddy ждёт этот ответ. В **3.1.5** `https://admin.<домен>` мог отвечать 502, пока API уже был healthy. В **3.1.4** эти контейнеры оставались в `Restarting` с `Read-only file system`. Первый `docker compose up` по-прежнему не роняет API: миграции backend и worker сериализованы (**3.1.4**, раздел 9.18). Если контейнер не стал healthy или панель перезапускается, скрипт печатает логи. Команда `curl | bash` читает вопросы с терминала SSH (это исправление **3.1.3**, раздел 9.17). Пошаговый разбор каждого вопроса — `INSTALL_STEPS.md`. Панели — раздел 9.19 `INSTRUCTION.md`. Сохранение секретов staging, `[CHECKOUT]` и production gate остаются от **3.1.1** (раздел 9.15). Обновление установленной копии: `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`. Уже работающий API **3.1.4** обновляйте этой командой и не выполняйте `docker compose down -v`.

Как скачать приложения: покупатель Android **2.10.0** — https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.10.0/remnawave_vpn_shop_android_user_2_10_0.apk , администратор Android **2.12.0** — https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.12.0/remnawave_vpn_shop_android_admin_2_12_0.apk . Рядом лежит файл `.sha256`, проверка — `sha256sum -c`. IPA в релизах нет: iOS собирается в Xcode из `mobile/ios-user` и `mobile/ios-admin`. Подробности — в `README.md`.

Version **3.1.6** does not change the database schema and does not replace the APKs. The admin UI, Mini App, and cabinet answer HTTP: nginx writes its pid and cache under `/tmp/nginx`, and Caddy waits for that answer. In **3.1.5** `https://admin.<domain>` could answer 502 while the API was already healthy. In **3.1.4** those containers stayed in `Restarting` with `Read-only file system`. The first `docker compose up` still does not drop the API: backend and worker migrations are serialized (the **3.1.4** fix, section 9.18). If a container does not become healthy or a panel keeps restarting, the script prints the logs. `curl | bash` reads questions from the SSH terminal (the **3.1.3** fix, section 9.17). Every prompt is in `INSTALL_STEPS.md`. The panels are section 9.19 of `INSTRUCTION.md`. Staging-secret preservation, `[CHECKOUT]`, and the production gate remain from **3.1.1** (section 9.15). Update an installed copy with `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`. Update a healthy **3.1.4** API with that command and do not run `docker compose down -v`.

How to download the apps: Android buyer **2.10.0** is https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.10.0/remnawave_vpn_shop_android_user_2_10_0.apk and Android administrator **2.12.0** is https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.12.0/remnawave_vpn_shop_android_admin_2_12_0.apk . A `.sha256` file sits beside each APK; check it with `sha256sum -c`. There is no IPA in the releases: iOS is built in Xcode from `mobile/ios-user` and `mobile/ios-admin`. The full steps are in `README.md`.

Файлы приложений, загруженные в панели, лежат в каталоге `app-packages` рядом с `MEDIA_DIR`. Этот каталог не публикуется как `/media`. Ссылки на скачивание описаны в разделе 9.11 `INSTRUCTION.md`.

App files uploaded in the panel live in `app-packages` next to `MEDIA_DIR`. That directory is not published as `/media`. Download links are described in section 9.11 of `INSTRUCTION.md`.

Рассылка Telegram включается тем же `BOT_TOKEN`, что и бот. Отдельной миграции в 2.12.0 нет: таблица `broadcasts` создана миграцией `0003_marketing`. Процесс бота должен быть запущен, иначе очередь не уйдёт в Telegram.

The Telegram broadcast uses the same `BOT_TOKEN` as the bot. Version 2.12.0 adds no migration: the `broadcasts` table comes from `0003_marketing`. The bot process must be running, otherwise the queue is not delivered.

Предыдущие установщики: 2.9.0 (debug APK), 2.8.0 (тексты и логотип приложений), 2.7.0 (приложения Android и iOS), 2.6.0 (платформа антиабьюза и агент узла), 2.5.0 (конструктор тарифов и мониторинг узлов) и 2.4.0 (личный кабинет). Серверная схема остаётся на миграции `0038_v2_6_0_platform`. Установщик VPS сервер ставит, а APK на телефон не копирует. Android-пакеты 2.10.0 лежат во вложениях релиза и собираются скриптом `scripts/build-android-apk.sh`. Пакеты 2.9.0 остаются в истории релиза. iOS собирается в Xcode. Тексты и логотип задаются в админке, раздел 9.7 `INSTRUCTION.md`. Установка APK 2.9.0 — раздел 9.8. Подпись клиента, release APK и обновление с GitHub — раздел 9.9. Проверка без касс — раздел 9.4. Агент — раздел 9.5. Лицензия — `LICENSE`.

English: the installer deploys the server. It does not copy an APK to a phone. The 2.10.0 release APKs are release attachments. The 2.9.0 debug APKs stay in that release's history. iOS is built in Xcode. Section 9.9 of `INSTRUCTION.md` covers client proof and `scripts/update-from-github.sh`. The schema stays `0038_v2_6_0_platform`.

## Что устанавливает скрипт

Текущая команда установки:

```bash
sudo bash install.sh
```

С версии 2.3.0 корневой `install.sh` передаёт управление `deploy/install-vps.sh`. С версии 2.4.0 скрипт также спрашивает `CABINET_DOMAIN`, VK OAuth, `PAYMENTS_SANDBOX` и `TRIAL_MAX_DAYS`. Секреты генерирует сам. `INSTALL_NONINTERACTIVE=1` берёт уже экспортированные переменные. Наружу открываются только SSH, TCP 80/443 и UDP 443.

Скрипт автоматически:

1. Проверяет root и Debian/Ubuntu.
2. Устанавливает Docker Engine/Compose и системные зависимости.
3. Запрашивает только инфраструктурные и провайдерские данные, которые невозможно безопасно угадать.
4. Генерирует `APP_SECRET`, пароль PostgreSQL и другие runtime secrets.
5. Создаёт `.env` с правами `0600`; ручное редактирование не требуется.
6. Явно пишет `BACKUP_S3_ENABLED=true/false`, поэтому отключённый S3 не ломает Pydantic Settings.
7. Генерирует `package-lock.json` для Admin, Mini App и Cabinet с таймаутом, после чего Docker использует `npm ci`.
8. Получает immutable digest для build-stage Python/Node/Nginx и runtime Redis/PostgreSQL/Caddy.
9. Записывает pinned runtime images в `.env` и `.env.images`.
10. Настраивает UFW: только SSH, TCP 80/443 и UDP 443. PostgreSQL/Redis/backend наружу не публикуются.
11. Включает Fail2Ban для SSH и unattended security updates.
12. Проверяет SSH-конфигурацию перед reload.
13. Собирает backend, worker, bot, admin, Mini App и личный кабинет.
14. Запускает PostgreSQL/Redis и выполняет health-check.
15. Применяет Alembic migrations.
16. Выводит URL панели, Mini App, кабинета и API.

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

Обновление с GitHub, когда магазин уже стоит в `/opt/vpn-shop`:

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

Скрипт 2.11.0 сверяет SHA-256, не затирает `.env` и просит `scripts/update.sh` снять снимок до замены файлов. Расписание cron не создаётся.

## English

Previous installers: 2.10.0 (release APKs and client proof), 2.9.0 (debug APK), 2.8.0 (app texts and logo), 2.7.0 (Android and iOS apps), 2.6.0 (abuse platform and node agent), 2.5.0 (tariff constructor and node monitoring) and 2.4.0 (user cabinet). The schema stays on migration `0038_v2_6_0_platform`. The VPS installer deploys the server. It does not copy an APK to a phone. The 2.10.0 APKs are release attachments. The 2.9.0 packages stay in that release. iOS is built in Xcode. App texts and the logo are section 9.7 of `INSTRUCTION.md`. The 2.9.0 APK install is section 9.8. Client proof, the release APK and the GitHub update are section 9.9. The gateway-free test is section 9.4. The agent is section 9.5. The license is `LICENSE`.

### What the script installs

```bash
sudo bash install.sh
```

Since 2.3.0 the root `install.sh` calls `deploy/install-vps.sh`. Since 2.4.0 the script also asks for `CABINET_DOMAIN`, VK OAuth, `PAYMENTS_SANDBOX` and `TRIAL_MAX_DAYS`. It generates secrets. `INSTALL_NONINTERACTIVE=1` uses variables that are already exported. The firewall opens SSH, TCP 80/443 and UDP 443 only.

The script checks root and Debian/Ubuntu, installs Docker Engine and Compose, asks only for values it cannot invent, generates `APP_SECRET` and the PostgreSQL password, writes `.env` as mode `0600`, records `BACKUP_S3_ENABLED` explicitly, generates `package-lock.json` for Admin, Mini App and Cabinet, pins image digests, configures UFW and Fail2Ban, checks SSH before reload, builds the backend, worker, bot, admin, Mini App and cabinet, starts PostgreSQL and Redis, applies Alembic migrations, and prints the panel, Mini App, cabinet and API URLs.

If the npm registry is unreachable, the install stops with an error instead of waiting forever.

### After install

2FA is not turned on automatically. Enable it in Admin → Безопасность.

```bash
cd /opt/vpn-shop
./scripts/preflight.sh
./scripts/security-scan.sh
./scripts/doctor.sh
```

Rebuild the current tree:

```bash
./scripts/update.sh
```

Roll back:

```bash
./scripts/rollback.sh
```

Update the whole project from the latest GitHub release:

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

The 2.11.0 script checks SHA-256, keeps `.env`, and asks `scripts/update.sh` to snapshot the install before replacing files. It does not create a cron job. Version 2.12.0 keeps that updater and adds the Telegram broadcast described in section 9.10 of `INSTRUCTION.md`. The buyer APK stays 2.10.0. The administrator APK is 2.12.0.

Run a staging end-to-end check with PostgreSQL, Redis, Remnawave and the sandbox provider before live payments.
