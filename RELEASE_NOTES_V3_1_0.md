# Remnawave VPN Shop 3.1.0

## Русский

Версия **3.1.0**. Предыдущий релиз — **3.0.1**. Схема базы остаётся `0038_v2_6_0_platform`. Новых APK и IPA нет: покупатель Android **2.10.0**, администратор Android **2.12.0**.

Исправления:

- `GET /api/plans` больше не возвращает `remnawave_profile_id`. Список тарифов в панели администратора это поле сохраняет.
- `GET /api/me/auto-renew` при сбое отвечает `last_error` = «Автопродление не выполнено» и не отдаёт текст исключения.

Новые функции:

- SHA-256 загруженного APK или IPA хранится в каталоге и показывается как `sha256`, когда ссылка на скачивание видна.
- `GET /api/public/apps/install` отдаёт карточки магазина, официальные ссылки GitHub и шаги установки на русском и английском.
- `GET /api/me/subscription-file` отдаёт ссылку подписки файлом `remnawave-subscription.txt`. В кабинете кнопка **Скачать подписку**.

Как скачать приложения:

- Покупатель Android 2.10.0: https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.10.0/remnawave_vpn_shop_android_user_2_10_0.apk и файл `.sha256` рядом. Проверка: `sha256sum -c remnawave_vpn_shop_android_user_2_10_0.apk.sha256`.
- Администратор Android 2.12.0: https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.12.0/remnawave_vpn_shop_android_admin_2_12_0.apk и файл `.sha256` рядом.
- iOS: IPA в релизах GitHub нет. Сборка в Xcode из `mobile/ios-user` и `mobile/ios-admin`. Кабинет отдаёт IPA только если администратор загрузил его на карточку.

## English

Version **3.1.0**. The previous release is **3.0.1**. The database schema stays `0038_v2_6_0_platform`. There is no new APK and no IPA: the Android buyer app stays **2.10.0** and the Android administrator app stays **2.12.0**.

Fixes:

- `GET /api/plans` no longer returns `remnawave_profile_id`. The administrator plan list still includes the field.
- `GET /api/me/auto-renew` sets `last_error` to «Автопродление не выполнено» after a failure and does not return the exception text.

New functions:

- The SHA-256 of an uploaded APK or IPA is stored in the catalog and shown as `sha256` when the download link is visible.
- `GET /api/public/apps/install` returns the shop cards, the official GitHub links and the install steps in Russian and English.
- `GET /api/me/subscription-file` returns the subscription URL as `remnawave-subscription.txt`. The cabinet button is **Скачать подписку** (Download subscription).

How to download the apps:

- Android buyer 2.10.0: https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.10.0/remnawave_vpn_shop_android_user_2_10_0.apk and the `.sha256` file beside it. Check with `sha256sum -c remnawave_vpn_shop_android_user_2_10_0.apk.sha256`.
- Android administrator 2.12.0: https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.12.0/remnawave_vpn_shop_android_admin_2_12_0.apk and the `.sha256` file beside it.
- iOS: GitHub releases do not include an IPA. Build it in Xcode from `mobile/ios-user` and `mobile/ios-admin`. The cabinet serves an IPA only after an administrator uploads it to the card.
