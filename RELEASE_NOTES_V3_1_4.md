# Release notes 3.1.4

## Русский

Установщик **3.1.4** доводит первый запуск до healthy API. Схема остаётся `0038_v2_6_0_platform`. Новых APK и IPA нет: покупатель Android остаётся **2.10.0**, администратор Android — **2.12.0**. Исправления **3.1.3** и **3.1.2** остаются. Production gate по-прежнему требует строку `FULL_E2E_PASS`.

### Что ломалось

На Ubuntu 24.04 команда `curl | bash` в **3.1.3** уже задавала вопросы и собирала образы. Затем `docker compose up` останавливался так:

```text
dependency failed to start: container vpn-shop-backend-1 is unhealthy
ERROR: installation failed at line 382
```

Backend и worker одновременно выполняли `alembic upgrade head`. Оба пытались создать `alembic_version`. PostgreSQL не делает `CREATE TABLE IF NOT EXISTS` безопасным для двух транзакций: второй процесс падал с `duplicate key value violates unique constraint "pg_type_typname_nsp_index"`. Контейнер API завершался за несколько секунд, не дожидаясь healthcheck. Логи при этом не печатались: `set -e` обрывал скрипт на `docker compose up`.

### Что изменено

- Перед созданием `alembic_version` миграция берёт `pg_advisory_xact_lock`. Второй процесс ждёт и затем видит уже применённую схему.
- Worker стартует только после healthy backend.
- Если `docker compose up` всё же падает, установщик печатает `docker compose ps` и последние логи backend и worker.
- Пробелы по краям ответа снимаются. `Moscow` записывается как `Europe/Moscow`. Цена проверяется как целое число. URL панели должен начинаться с `https://`.

### Повтор после неудачной 3.1.3

Каталог `/opt/vpn-shop` от оборванной установки нужно убрать вместе с томами. Это стирает базу той попытки. Рабочий магазин так не сбрасывайте.

```bash
cd /opt/vpn-shop && docker compose down -v
rm -rf /opt/vpn-shop /opt/vpn-shop-src
curl -fsSL https://raw.githubusercontent.com/booarkz-cpu/remnawave-vpn-shop/main/install.sh | sudo bash
```

Уже работающую копию обновляйте так: `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`.

## English

Installer **3.1.4** brings the first boot to a healthy API. The schema stays `0038_v2_6_0_platform`. There is no new APK and no IPA: the Android buyer app stays **2.10.0** and the Android administrator app stays **2.12.0**. The **3.1.3** and **3.1.2** fixes remain. The production gate still requires the line `FULL_E2E_PASS`.

### What failed

On Ubuntu 24.04, `curl | bash` in **3.1.3** already asked the questions and built the images. Then `docker compose up` stopped like this:

```text
dependency failed to start: container vpn-shop-backend-1 is unhealthy
ERROR: installation failed at line 382
```

Backend and worker both ran `alembic upgrade head`. Both tried to create `alembic_version`. PostgreSQL does not make `CREATE TABLE IF NOT EXISTS` safe for two transactions: the second process failed with `duplicate key value violates unique constraint "pg_type_typname_nsp_index"`. The API container exited within a few seconds, before the healthcheck window. The script printed no logs: `set -e` stopped it on `docker compose up`.

### What changed

- The migration takes `pg_advisory_xact_lock` before creating `alembic_version`. The second process waits and then sees the schema already applied.
- The worker starts only after the backend is healthy.
- If `docker compose up` still fails, the installer prints `docker compose ps` and the latest backend and worker logs.
- Surrounding spaces are removed from answers. `Moscow` is stored as `Europe/Moscow`. A price must be an integer. The panel URL must start with `https://`.

### Retry after a failed 3.1.3

Remove `/opt/vpn-shop` from the interrupted install together with its volumes. That deletes the database of that attempt. Do not reset a working shop this way.

```bash
cd /opt/vpn-shop && docker compose down -v
rm -rf /opt/vpn-shop /opt/vpn-shop-src
curl -fsSL https://raw.githubusercontent.com/booarkz-cpu/remnawave-vpn-shop/main/install.sh | sudo bash
```

Update a copy that is already running with `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`.
