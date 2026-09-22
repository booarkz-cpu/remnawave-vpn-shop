# Remnawave VPN Shop 3.0.0-realise

## Русский

Релиз закрывает критические ошибки, найденные при полном проходе `PRODUCTION_CHECKLIST.md` и аудите API. Новых таблиц нет: голова миграции остаётся `0038_v2_6_0_platform`. Новых APK и IPA нет. Покупатель остаётся `remnawave_vpn_shop_android_user_2_10_0.apk` (`versionName` 2.10.0). Администратор остаётся `remnawave_vpn_shop_android_admin_2_12_0.apk` (`versionName` 2.12.0, `versionCode` 2120).

Лицензия прежняя: Remnawave VPN Shop Proprietary License 1.0, файл `LICENSE`.

### Исправления

1. Загрузка APK и IPA на `POST /api/admin/apps/{id}/file` принимала в маршруте до 80 МБ, а общий фильтр тела обрывал запрос на 12 МБ. Теперь при наличии `Content-Length` предел этого маршрута равен 80 МБ. Запрос без длины остаётся на 12 МБ.
2. Право `manage_content` проверяется до чтения `UploadFile` и для пакета, и для логотипа.
3. Клиенты Telegram (`send_alert`, уведомление об истечении, `setMyName`), Яндекс OAuth и Remnawave создаются с `trust_env=False`. Прокси из `HTTP_PROXY` / `HTTPS_PROXY` не получает URL с токеном.
4. `X-Forwarded-For` читается только если соседний адрес — loopback, частная сеть или link-local. Caddy в Docker по-прежнему передаёт адрес клиента. Прямое обращение к API не подменяет IP вебхука.
5. Повтор выдачи платежа и операции, а также сводка здоровья, больше не возвращают текст исключения. В JSON остаётся «Повтор выдачи не выполнен» или `unavailable`. Подробность пишется в журнал.
6. `scripts/sandbox-e2e.sh` вызывает `python3`, если команды `python` нет.
7. Чистая установка доходит до `0038_v2_6_0_platform`. `alembic_version.version_num` создаётся как `VARCHAR(128)`. Миграция `0027` не удаляет уже снятое ограничение `uq_payment_provider_events_event_id`. Миграция `0033` добавляет `audit_logs.request_id` через `add_column`.
8. Хеш пароля scrypt с `n=2**15` и `r=8` больше не упирается в предел памяти OpenSSL 32 МиБ. Сложность та же, `maxmem` равен 64 МиБ и при записи, и при проверке.
9. Создание тарифа больше не падает с 500. Модель `AuditLog` хранит `request_id`, а журнал сериализует `Decimal` и дату.
10. Флаги функций ищутся по колонке `key`, а не по числовому `id`. Создание платежа больше не получает 500 на пустой таблице `feature_flags`.
11. Vite в `admin`, `miniapp` и `cabinet` поднят с `7.1.5` до `7.3.6`. Это закрывает предупреждения `npm audit` уровня high для dev-сервера. Собранные статические файлы по-прежнему отдаёт Caddy, а не Vite.

### Что проверить на своём сервере

Живой VPS, файрвол, S3, SMTP, кассы YooKassa / Platega / RollyPay, Xcode и установка APK на телефон в этой сборке не выполнялись. На сервере пройдите оставшиеся пункты `PRODUCTION_CHECKLIST.md`: `docker compose up -d`, `scripts/doctor.sh`, резервная копия и тестовое восстановление, затем один платёж на тестовом магазине.

Обновление установленной копии:

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

Снимок и `pg_dump` создаются до копирования файлов. `.env` сохраняется. Cron не включается.

## English

This release closes critical defects found while walking `PRODUCTION_CHECKLIST.md` and auditing the API. There is no new table. The migration head stays `0038_v2_6_0_platform`. There is no new APK and no IPA. The buyer app stays `remnawave_vpn_shop_android_user_2_10_0.apk` (`versionName` 2.10.0). The administrator app stays `remnawave_vpn_shop_android_admin_2_12_0.apk` (`versionName` 2.12.0, `versionCode` 2120).

The license is unchanged: Remnawave VPN Shop Proprietary License 1.0, file `LICENSE`.

### Fixes

1. APK and IPA upload on `POST /api/admin/apps/{id}/file` allowed 80 MB in the route, while the global body filter cut the request at 12 MB. With `Content-Length`, that route now allows 80 MB. A request without a length stays at 12 MB.
2. The `manage_content` permission is checked before `UploadFile` is read, for both the package and the logo.
3. The Telegram clients (`send_alert`, the expiry notice, `setMyName`), Yandex OAuth and Remnawave are created with `trust_env=False`. A proxy from `HTTP_PROXY` / `HTTPS_PROXY` does not receive a URL that contains a token.
4. `X-Forwarded-For` is read only when the peer address is loopback, private or link-local. Caddy on Docker still forwards the client address. A direct call to the API cannot spoof a webhook IP.
5. Payment retry, provisioning retry and the health summary no longer return exception text. The JSON says «Повтор выдачи не выполнен» or `unavailable`. The detail is written to the log.
6. `scripts/sandbox-e2e.sh` calls `python3` when the `python` command is absent.
7. A fresh install reaches `0038_v2_6_0_platform`. `alembic_version.version_num` is created as `VARCHAR(128)`. Migration `0027` does not drop the already removed constraint `uq_payment_provider_events_event_id`. Migration `0033` adds `audit_logs.request_id` with `add_column`.
8. The scrypt password hash with `n=2**15` and `r=8` no longer hits OpenSSL's 32 MiB memory ceiling. The work factor is unchanged. `maxmem` is 64 MiB for both hashing and verification.
9. Creating a plan no longer returns 500. The `AuditLog` model stores `request_id`, and the log serializes `Decimal` values and dates.
10. Feature flags are loaded by the `key` column, not by the numeric `id`. Creating a payment no longer returns 500 on an empty `feature_flags` table.
11. Vite in `admin`, `miniapp` and `cabinet` moves from `7.1.5` to `7.3.6`. That clears the high `npm audit` findings for the dev server. Built static files are still served by Caddy, not by Vite.

### What to check on your server

A live VPS, the firewall, S3, SMTP, the YooKassa / Platega / RollyPay gateways, Xcode and installing an APK on a phone were not run in this build. On the server, finish the remaining items in `PRODUCTION_CHECKLIST.md`: `docker compose up -d`, `scripts/doctor.sh`, a backup and a test restore, then one payment in a test shop.

Update an installed copy:

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

The snapshot and `pg_dump` are created before files are copied. `.env` is kept. Cron is not enabled.
