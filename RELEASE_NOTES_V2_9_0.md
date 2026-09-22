# Remnawave VPN Shop 2.9.0

Релиз **2.9.0** публикует устанавливаемые Android-пакеты покупателя и администратора, исправляет ошибки сборки и открытия платёжной ссылки и обновляет документацию. Исходники iOS остаются в репозитории. IPA собирается в Xcode на macOS.

The **2.9.0** release publishes installable Android packages for the buyer and the administrator, fixes the payment-link check and the iOS payment screen compile error, and updates the documentation. The iOS sources stay in the repository. The IPA is built with Xcode on macOS.

## Что вошло

- Два debug-подписанных APK для ручной установки: `remnawave_vpn_shop_android_user_2_9_0.apk` и `remnawave_vpn_shop_android_admin_2_9_0.apk`. Файлы лежат во вложениях GitHub Release вместе с `.sha256`. В git и в zip исходников их нет.
- Скрипт `scripts/build-android-apk.sh` собирает оба пакета командой `:app:assembleDebug` (SDK 35, minSdk 26, versionName `2.9.0`).
- User-Agent: `RemnawaveShop-Android-User/2.9.0`, `RemnawaveShop-Android-Admin/2.9.0`, `RemnawaveShop-iOS-User/2.9.0`, `RemnawaveShop-iOS-Admin/2.9.0`. Новая строка начинает новую сессию.
- Платёжная ссылка Android разбирается как URL. Принимается `https`. `http` принимается только для хостов `localhost`, `127.0.0.1` и `10.0.2.2`. Логин в адресе и пробелы отклоняются.
- В приложении iOS покупателя константа локальных хостов видна экрану оплаты, поэтому проект собирается в Xcode.
- Схема базы не менялась. Голова миграций остаётся `0038_v2_6_0_platform`.
- Лицензия прежняя: Remnawave VPN Shop Proprietary License 1.0 (`LicenseRef-Proprietary`).

## Установка APK

Разрешите установку из выбранного источника, скачайте APK с релиза и откройте файл. Через adb:

```bash
adb install -r remnawave_vpn_shop_android_user_2_9_0.apk
adb install -r remnawave_vpn_shop_android_admin_2_9_0.apk
```

Пакеты подписаны отладочным ключом машины сборки. Это сборка для ручной установки. Для Google Play нужна отдельная подпись владельца. Сборка на другой машине может потребовать удалить уже установленную копию, если отладочный ключ отличается.

## iOS

Откройте `mobile/ios-user/VpnShopUser.xcodeproj` и `mobile/ios-admin/VpnShopAdmin.xcodeproj` в Xcode 15 или новее, выберите команду подписи и соберите приложение. IPA создаёт Product → Archive. На хосте этого релиза Xcode нет, поэтому IPA во вложениях нет.

## English

The release attaches two debug-signed sideload APKs, `remnawave_vpn_shop_android_user_2_9_0.apk` and `remnawave_vpn_shop_android_admin_2_9_0.apk`, plus `.sha256` files. They are not committed and they are not inside the source zip. `scripts/build-android-apk.sh` runs `:app:assembleDebug`.

The app User-Agent strings are `RemnawaveShop-Android-User/2.9.0`, `RemnawaveShop-Android-Admin/2.9.0`, `RemnawaveShop-iOS-User/2.9.0` and `RemnawaveShop-iOS-Admin/2.9.0`. A new string starts a new session.

The Android payment URL is parsed. `https` is accepted. `http` is accepted only for `localhost`, `127.0.0.1` and `10.0.2.2`. User info and whitespace are rejected. The iOS buyer app exposes the local-host set to the payment screen so the Xcode project compiles.

The migration head stays `0038_v2_6_0_platform`. The license stays Remnawave VPN Shop Proprietary License 1.0.

Install with `adb install -r` or by opening the APK after allowing installs from that source. The packages use the build machine's debug key. A Play Store upload needs the owner's signing key.

Open `mobile/ios-user/VpnShopUser.xcodeproj` and `mobile/ios-admin/VpnShopAdmin.xcodeproj` in Xcode 15 or newer and archive there. This release host has no Xcode, so the release has no IPA.

## Лицензия

Лицензия прежняя: Remnawave VPN Shop Proprietary License 1.0 (`LicenseRef-Proprietary`). Файл `LICENSE` покрывает веб-кабинет, админку и приложения Android и iOS.
