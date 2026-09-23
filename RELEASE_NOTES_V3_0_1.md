# Remnawave VPN Shop 3.0.1

## Русский

Релиз закрывает критические ошибки, найденные после **3.0.0-realise**. Новых таблиц нет: голова миграции остаётся `0038_v2_6_0_platform`. Новых APK и IPA нет. Покупатель остаётся `remnawave_vpn_shop_android_user_2_10_0.apk` (`versionName` 2.10.0). Администратор остаётся `remnawave_vpn_shop_android_admin_2_12_0.apk` (`versionName` 2.12.0, `versionCode` 2120).

Лицензия прежняя: Remnawave VPN Shop Proprietary License 1.0, файл `LICENSE`.

### Исправления

1. Автопродление YooKassa и проверка шифрованной резервной копии вызывали `backend.app.security`. В контейнере процесс запущен как `app.main`, этого модуля нет, продление записывало ошибку и пропускало списание, а `POST /api/admin/backups/{id}/validate` отвечал 500. Теперь используется `decrypt_secret` из пакета `app`. Конфиг staging E2E читает тот же импорт.
2. `POST /api/me/wallet/spend` без `Idempotency-Key` больше не создаёт случайный ключ на каждый запрос. Заголовок обязателен. Повтор с тем же ключом под блокировкой пользователя возвращает уже созданный платёж.
3. Второй запрос с другим ключом на тот же тариф, ту же цену и тот же промокод в течение 30 секунд отвечает 409 «Повторное списание с баланса заблокировано. Подождите полминуты и повторите покупку.» Баланс не списывается второй раз. Уже установленные приложения покупателя 2.10.0 защищены этим правилом на сервере.
4. `POST /api/me/gifts/purchase` ищет подарок по ключу идемпотентности ещё раз под блокировкой пользователя. Параллельный повтор не создаёт второй код.
5. `POST /api/payments/create` держит блокировку `lock:checkout-intent` на пользователя. Новый ключ не открывает второй сеанс провайдера, пока за последние 30 секунд есть незавершённый счёт на тот же снимок тарифа. Счёт в состоянии `pending` возвращается снова.

### Что проверить на своём сервере

Обновление установленной копии:

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

Снимок и `pg_dump` создаются до копирования файлов. `.env` сохраняется. Cron не включается. После обновления включите автопродление на тестовом аккаунте и проверьте, что в журнале нет `ModuleNotFoundError`. Двойное нажатие оплаты с баланса должно оставить одно списание.

## English

This release closes critical defects found after **3.0.0-realise**. There is no new table. The migration head stays `0038_v2_6_0_platform`. There is no new APK and no IPA. The buyer app stays `remnawave_vpn_shop_android_user_2_10_0.apk` (`versionName` 2.10.0). The administrator app stays `remnawave_vpn_shop_android_admin_2_12_0.apk` (`versionName` 2.12.0, `versionCode` 2120).

The license is unchanged: Remnawave VPN Shop Proprietary License 1.0, file `LICENSE`.

### Fixes

1. YooKassa auto-renew and encrypted backup validation imported `backend.app.security`. The container runs `app.main`, so that module does not exist. Renewal stored an error and skipped the charge, and `POST /api/admin/backups/{id}/validate` answered 500. Both now call `decrypt_secret` from the `app` package. The staging E2E config uses the same import.
2. `POST /api/me/wallet/spend` no longer invents a random key when `Idempotency-Key` is missing. The header is required. A retry with the same key, while the user row is locked, returns the payment already created.
3. A second request with a different key for the same plan, price and promo code within 30 seconds answers 409 «Повторное списание с баланса заблокировано. Подождите полминуты и повторите покупку.» The balance is not debited again. Installed buyer apps at 2.10.0 are covered by this server rule.
4. `POST /api/me/gifts/purchase` looks up the gift by idempotency key again while the user row is locked. A parallel retry does not create a second code.
5. `POST /api/payments/create` holds `lock:checkout-intent` for the user. A new key does not open a second provider session while an unfinished invoice for the same plan snapshot exists from the last 30 seconds. A `pending` invoice is returned again.

### What to check on your server

Update an installed copy:

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

The snapshot and `pg_dump` are created before files are copied. `.env` is kept. Cron is not enabled. After the update, enable auto-renew on a test account and confirm the log has no `ModuleNotFoundError`. A double tap on wallet payment must leave a single debit.
