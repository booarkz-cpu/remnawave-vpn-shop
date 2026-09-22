# Remnawave VPN Shop 2.10.0

Схема базы остаётся `0038_v2_6_0_platform`. Лицензия остаётся Remnawave VPN Shop Proprietary License 1.0 (`LicenseRef-Proprietary`).

The database schema stays `0038_v2_6_0_platform`. The license stays the Remnawave VPN Shop Proprietary License 1.0 (`LicenseRef-Proprietary`).

## Android

Два APK для ручной установки, подписанные release-ключом этой сборки:

- `remnawave_vpn_shop_android_user_2_10_0.apk`
- `remnawave_vpn_shop_android_admin_2_10_0.apk`

Рядом лежат файлы `.sha256`. Пакетов в git и в zip исходников нет. Это не сборка Google Play.

`versionName` — `2.10.0`, `versionCode` — `2100`. Сертификат подписи, SHA-256:

`9D:53:E2:3D:4E:23:96:6A:5E:44:95:10:D4:76:49:41:44:A3:8C:69:DE:CA:05:0A:98:A7:01:9C:65:A6:1A:A4`

Закрытый ключ в релиз не входит. Следующая сборка с тем же ключом ставится поверх этой. Пакеты 2.9.0 были подписаны debug-ключом, поэтому перед установкой 2.10.0 их нужно удалить один раз.

Повторная сборка: задайте `ANDROID_HOME`, `GRADLE_BIN`, `ANDROID_KEYSTORE`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD` и выполните `bash scripts/build-android-apk.sh /tmp/apk`. Без keystore скрипт собирает debug APK.

Two sideload APKs are signed with this build's release key. They are not a Play Store upload and they are not in git. `versionName` is `2.10.0` and `versionCode` is `2100`. The certificate SHA-256 is the value above. The private key is not attached. A later build with the same key installs over this one. The 2.9.0 packages were debug-signed, so uninstall those once before installing 2.10.0.

## iOS

Исходники `mobile/ios-user` и `mobile/ios-admin` открываются в Xcode на macOS. `MARKETING_VERSION` — `2.10.0`, `CURRENT_PROJECT_VERSION` — `2100`. IPA на этой Linux-сборке не создаётся: Xcode здесь нет.

The iOS sources open in Xcode on macOS. This Linux build does not produce an IPA because Xcode is not available here.

## Покупатель / Buyer

- QR подписки: `GET /api/me/connection-qr` (нужна сессия). Приложение грузит PNG с bearer и подписью, без редиректов, не больше 2 МБ.
- Кнопки Happ, v2rayNG и Streisand строят ссылки `happ://add/{url}`, `v2rayng://install-sub?url={url}` и `streisand://import/{url}` только для `https://` без пробелов.
- Устройства: `GET /api/me/devices` и `POST /api/me/devices/{id}/revoke`. Ответ списка не содержит `device_key` и `last_ip`.
- Трафик: `GET /api/me/traffic`. Если Remnawave недоступен, лимит берётся из снимка подписки, расход остаётся пустым, `available` равен false.
- Подарок: `POST /api/me/gifts/redeem` с полем `code` длиной 4–64.
- Пополнение кошелька: `POST /api/me/wallet/topup` с суммой 50–100000, провайдером и заголовком `Idempotency-Key`. Провайдер `sandbox` проходит без production gate, когда `PAYMENTS_SANDBOX=true`.
- Ссылка оплаты открывается только для `https` либо для `http` на `localhost`, `127.0.0.1` и `10.0.2.2`, без логина в адресе и без пробелов.
- Сохранённый токен закрыт биометрией или PIN устройства. Если устройство не умеет это, экран открывается сразу. Выход остаётся доступен. Свежий вход по паролю экран не запирает.

The buyer app shows the subscription QR, opens Happ, v2rayNG and Streisand, lists devices without `device_key` or `last_ip`, shows traffic, redeems a gift and tops up the wallet. A saved token asks for biometrics or the device PIN. A device that cannot authenticate opens immediately. A fresh password login stays unlocked.

## Подпись клиента / Client proof

Приложения шлют `X-Shop-Client`, `X-Shop-Time` и `X-Shop-Proof`. Сообщение HMAC-SHA256: `{client}\n{unix}\n{METHOD}\n{path}` без query. Окно — 300 секунд. Неверная подпись отвечает 401 «Подпись клиента не принята».

Проверка включается, когда заголовок клиента известен, `MOBILE_REQUIRE_PROOF=true` и `MOBILE_CLIENT_KEY` не пуст. Браузер без `X-Shop-Client` работает как раньше, на cookie.

Ключ по умолчанию лежит в исходниках и в APK. Его можно извлечь. Свой ключ задаётся в `.env` и требует пересборки приложений. `MOBILE_REQUIRE_PROOF=false` оставляет рабочими приложения 2.9.0 после обновления сервера.

The apps send an HMAC of the client name, the unix time, the method and the path. The default key is in the source and in the APK, so it can be extracted. Set `MOBILE_REQUIRE_PROOF=false` to keep 2.9.0 apps working after the server upgrade.

User-Agent этой версии: `RemnawaveShop-Android-User/2.10.0`, `RemnawaveShop-Android-Admin/2.10.0`, `RemnawaveShop-iOS-User/2.10.0`, `RemnawaveShop-iOS-Admin/2.10.0`. Смена строки начинает новую сессию. Строки 2.9.0 остаются в истории.

## Уведомления / Notices

Планировщик срока подписки шлёт в Telegram русскую фразу и английскую: «Your VPN subscription expires on {date}. Open the shop to renew.» После успешного пополнения и после успешной выдачи подписки вызывается `notify_user_telegram`. Ошибка отправки пишется в журнал и не откатывает платёж. Нет `chat_id` или `BOT_TOKEN` — отправки нет.

## Админ-приложение / Admin app

Полное редактирование тарифов и брендинга остаётся в веб-админке.

- `POST /api/admin/plans/{id}/enabled` с `{"enabled": true|false}` требует `manage_plans`.
- `GET /api/admin/payments/{id}` требует `read` и отдаёт id, user_id, plan_id, provider, purpose, order_id, amount, currency, status, fulfillment_status, created_at, paid_at. Поля `fulfillment_error`, `checkout_url` и `provider_payment_id` не отдаются. Список платежей тоже не отдаёт `fulfillment_error`.
- Сводка платформы помечает агента `stale=true`, если `last_seen_at` пуст или старше 5 минут.

## Обновление с GitHub / GitHub update

API не распаковывает архив и не применяет обновление. `GET /api/admin/github-update` (право `ops.releases`) показывает репозиторий, текущую версию, тег GitHub и команду:

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

Скрипт скачивает последний релиз `booarkz-cpu/remnawave-vpn-shop`, принимает только zip `full_release` и соседний `.sha256`, отклоняет чужой хост и пути с `..`, сохраняет `.env`, `.env.*`, `.rollback` и `.git`, затем запускает существующий `scripts/update.sh` (снимок, `pg_dump`, сборка, проверка, откат при ошибке). Если тег не новее установленной версии, скрипт печатает «Установлена актуальная версия» и выходит с кодом 0. Cron по желанию администратора, по умолчанию он не включён.

The API does not extract the archive. The host script verifies SHA-256, keeps `.env`, and runs the existing `scripts/update.sh`. A cron job is optional and is not enabled by default.
