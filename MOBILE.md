# Мобильные приложения 3.1.6 / Mobile apps 3.1.6

Серверная версия **3.1.6** не меняет пакеты Android и проекты iOS. Покупатель остаётся **2.10.0**, администратор — **2.12.0**. То же было в **3.1.5**, **3.1.4**, **3.1.3**, **3.1.2**, **3.1.1** и **3.1.0**: загруженный APK или IPA получает SHA-256, и кабинет показывает её рядом с кнопкой **Скачать**. Файл подписки скачивается кнопкой **Скачать подписку**. Повторное нажатие «оплатить с баланса» по-прежнему не списывает сумму второй раз: это исправление **3.0.1**, сервер требует `Idempotency-Key`.

Как скачать сборки репозитория: покупатель https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.10.0/remnawave_vpn_shop_android_user_2_10_0.apk , администратор https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.12.0/remnawave_vpn_shop_android_admin_2_12_0.apk . Проверка — `sha256sum -c` по соседнему файлу `.sha256`. IPA нет: Xcode, каталоги `mobile/ios-user` и `mobile/ios-admin`.

Server version **3.1.6** does not change the Android packages or the iOS projects. The buyer app stays **2.10.0** and the administrator app stays **2.12.0**. The same was true in **3.1.5**, **3.1.4**, **3.1.3**, **3.1.2**, **3.1.1**, and **3.1.0**: an uploaded APK or IPA receives a SHA-256, and the cabinet shows it beside **Скачать** (Download). The subscription file is downloaded with **Скачать подписку** (Download subscription). A second tap on “pay from balance” still does not debit the amount again: that is the **3.0.1** fix, and the server requires `Idempotency-Key`.

Repository builds: buyer https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.10.0/remnawave_vpn_shop_android_user_2_10_0.apk , administrator https://github.com/booarkz-cpu/remnawave-vpn-shop/releases/download/v2.12.0/remnawave_vpn_shop_android_admin_2_12_0.apk . Check them with `sha256sum -c` against the neighbouring `.sha256` file. There is no IPA: use Xcode and the directories `mobile/ios-user` and `mobile/ios-admin`.

С версии **2.13.0** ссылка на скачивание приложения администратора стоит в веб-панели, а ссылка на приложение покупателя — в личном кабинете. Сами пакеты Android остаются **2.12.0** для администратора и **2.10.0** для покупателя, пока администратор не загрузит новый файл.

From **2.13.0** the administrator app download link is in the web panel, and the buyer app download link is in the user cabinet. The Android packages stay **2.12.0** for the administrator and **2.10.0** for the buyer until an administrator uploads a new file.

Администратор Android и iOS в этом релизе — **2.12.0**. Покупатель остаётся **2.10.0**. The administrator Android and iOS apps in this release are **2.12.0**. The buyer app stays **2.10.0**.

Текущая версия приложений покупателя **2.10.0**. Исходники появились в **2.7.0**. В **2.8.0** администратор задаёт тексты карточек и общий логотип. В **2.9.0** релиз GitHub содержит debug APK покупателя и администратора. В **2.10.0** APK подписаны release-ключом, добавлены QR, глубокие ссылки, устройства, трафик, подарок, пополнение, подпись HMAC и биометрия.

The current app version is **2.10.0**. The sources arrived in **2.7.0**. In **2.8.0** an administrator edits the cards and the shared logo. In **2.9.0** the GitHub release contains debug APKs for the buyer and the administrator. In **2.10.0** the APKs are release-signed and add a QR, deep links, devices, traffic, gifts, top-up, HMAC proof and a biometric lock.

Четыре отдельных клиента магазина: Android и iOS для покупателя, Android и iOS для администратора. Общий вид — тёмная схема Material Design и акцент Web 3.0 `#00E5C0`. В каждом приложении есть переключатель **RU / EN**.

Four separate shop clients: Android and iOS for the buyer, Android and iOS for the administrator. The shared look is a dark Material Design scheme with the Web 3.0 accent `#00E5C0`. Each app has a **RU / EN** language switch.

Русский и English живут в одном каталоге на роль: `mobile/l10n/user.json` и `mobile/l10n/admin.json`. Копии лежат в assets Android и в бандле iOS и должны совпадать побайтно.

## Логотип и карточки

Админка, вкладка **Приложения**, сохраняет четыре карточки и файл `client_logo`. Покупательский кабинет читает `GET /api/public/apps` и показывает логотип и включённые карточки покупателя. Приложения на экране входа запрашивают тот же публичный маршрут. После входа администраторское приложение читает `GET /api/admin/apps`. Картинка загружается только с пути `/media/<имя>`, без редиректа.

The admin **Приложения** tab stores four cards and the `client_logo` file. The buyer cabinet reads `GET /api/public/apps` and shows the logo plus enabled buyer cards. The apps request the same public route on the sign-in screen. After sign-in the administrator app reads `GET /api/admin/apps`. The image download accepts only a `/media/<name>` path and does not follow redirects.

## Лицензия

Приложения входят в Remnawave VPN Shop и покрываются **Remnawave VPN Shop Proprietary License 1.0** (`SPDX-License-Identifier: LicenseRef-Proprietary`). Полный текст — корневой файл `LICENSE`. Краткая отсылка — `mobile/LICENSE`.

The apps are part of Remnawave VPN Shop and are covered by the Remnawave VPN Shop Proprietary License 1.0. The full text is the root `LICENSE` file. `mobile/LICENSE` is a short pointer.

## Состав

| Приложение | Каталог | Идентификатор | `X-Shop-Client` | User-Agent |
| --- | --- | --- | --- | --- |
| Android, покупатель | `mobile/android-user` | `shop.remnawave.user` | `android-user` | `RemnawaveShop-Android-User/2.10.0` |
| Android, администратор | `mobile/android-admin` | `shop.remnawave.admin` | `android-admin` | `RemnawaveShop-Android-Admin/2.12.0` |
| iOS, покупатель | `mobile/ios-user` | `shop.remnawave.user` | `ios-user` | `RemnawaveShop-iOS-User/2.10.0` |
| iOS, администратор | `mobile/ios-admin` | `shop.remnawave.admin` | `ios-admin` | `RemnawaveShop-iOS-Admin/2.12.0` |

User-Agent должен оставаться одинаковым между входом и следующими запросами: сессия привязана к нему, смена строки отзывает сессию. Предыдущие строки сессии 2.9.0: `RemnawaveShop-Android-User/2.9.0`, `RemnawaveShop-Android-Admin/2.9.0`, `RemnawaveShop-iOS-User/2.9.0`, `RemnawaveShop-iOS-Admin/2.9.0`. Строка администратора 2.10.0 была `RemnawaveShop-Android-Admin/2.10.0` и `RemnawaveShop-iOS-Admin/2.10.0`. Строка 2.12.0 начинает новую сессию администратора. Покупатель остаётся на `2.10.0`.

## Рассылка в приложении администратора

Вкладка **Рассылка** читает `GET /api/admin/marketing` и показывает очередь. Кнопка отправки вызывает `POST /api/admin/broadcasts` с полями `text` и `target` (`all`, `active`, `inactive`). Кнопка повтора вызывает `POST /api/admin/broadcasts/{id}/retry` для статусов `sending` и `failed`. Право на запись — `manage_broadcasts`. Доставку выполняет бот, не само приложение.

The **Broadcast** tab reads `GET /api/admin/marketing` and shows the queue. Queue calls `POST /api/admin/broadcasts` with `text` and `target` (`all`, `active`, `inactive`). Retry calls `POST /api/admin/broadcasts/{id}/retry` for `sending` and `failed`. The write permission is `manage_broadcasts`. The bot delivers the message. The app does not.

The previous 2.9.0 session strings were `RemnawaveShop-Android-User/2.9.0`, `RemnawaveShop-Android-Admin/2.9.0`, `RemnawaveShop-iOS-User/2.9.0` and `RemnawaveShop-iOS-Admin/2.9.0`. The 2.10.0 string starts a new session.

The User-Agent must stay the same between sign-in and later calls. The session is bound to it, and a changed string revokes the session.

## Как устроена сессия

Веб-кабинет и веб-админка по-прежнему получают JWT только в HttpOnly cookie. Нативные приложения отправляют заголовок `X-Shop-Client` с одним из четырёх имён выше. Только тогда `session_body()` в `backend/app/mobile_auth.py` добавляет в JSON `access_token` и `token_type: bearer` и обработчик не ставит cookie.

Дальше приложение шлёт `Authorization: Bearer <token>` и не сохраняет `Set-Cookie`. Если заголовка `X-Shop-Client` нет или имя не из списка, JSON входа токен не содержит.

CSRF для cookie-мутаций на мобильный Bearer не распространяется: клиент cookie не присылает. Вход и регистрация и так исключены из CSRF.

The web cabinet and the web admin still receive the JWT only in an HttpOnly cookie. Native apps send `X-Shop-Client` with one of the four names above. Only then `session_body()` in `backend/app/mobile_auth.py` adds `access_token` and `token_type: bearer` to the JSON, and the handler does not set a cookie.

Later calls send `Authorization: Bearer <token>` and do not persist `Set-Cookie`. Without a known `X-Shop-Client` value, the login JSON does not contain the token.

## Адрес API

Принимается `https://`. `http://` разрешён только для `localhost`, `127.0.0.1` и `10.0.2.2` (эмулятор Android). Адрес с логином, паролем или пробелом отклоняется. Редиректы HTTP клиенты не следуют. Платёжная ссылка открывается только для `https` или тех же локальных `http` хостов.

`https://` is required. `http://` is allowed only for `localhost`, `127.0.0.1` and `10.0.2.2` (the Android emulator). A URL with user info or whitespace is rejected. The HTTP clients do not follow redirects. A payment URL opens only for `https` or those same local `http` hosts.

Правила продублированы в Kotlin, Swift и в `mobile/client_rules.py`, который проверяет pytest.

## Функции покупателя

| Экран | Действие | Маршрут |
| --- | --- | --- |
| Вход | email и пароль от 8 символов | `POST /api/auth/login` |
| Регистрация | тот же набор полей | `POST /api/auth/register` |
| Обзор | кошелёк, реферальный код, срок подписки | `GET /api/me/dashboard` |
| Тарифы | оплата провайдером и промокод | `POST /api/payments/create` с `Idempotency-Key` |
| Тарифы | списание баланса | `POST /api/me/wallet/spend` с `Idempotency-Key` |
| Конструктор | первая включённая комбинация устройств, трафика и дней | `POST /api/payments/create` с `constructor_id`, `device_option_id`, `traffic_option_id`, `days_option_id` |
| Серверы | имя, страна, статус, пользователи онлайн | `GET /api/me/servers` |
| Подключение | ссылка, копирование, инструкции Android, iOS, TV, Windows, macOS, Linux | `GET /api/me/connection-info` |
| Подключение | пробный период по первому тарифу и `trial_days` | `POST /api/me/trial` |
| Поддержка | тема и сообщение | `POST /api/me/support/tickets` |
| Язык | перечитывает каталог и `Accept-Language` | локально |

Провайдер оплаты берётся из `GET /api/public/config`: если в `payment_providers` есть `sandbox`, выбирается он, иначе первый провайдер списка.

Якорь конструктора скрыт из `GET /api/plans`. Прямая покупка и пробный период якорного `plan_id` сервер отклоняет.

Список узлов на клиенте ещё раз оставляет только `name`, `country`, `status`, `users_online`. Имя с `://` или похожее на IP заменяется на `node`.

Инструкции подключения: если `Accept-Language` начинается с `en`, сервер отдаёт английские тексты по умолчанию, иначе русские. Сохранённые администратором `guide_*` перекрывают значения по умолчанию.

## Функции администратора

| Экран | Действие | Маршрут |
| --- | --- | --- |
| Вход | email, пароль, код 2FA только если поле не пустое | `POST /api/admin/auth/login` |
| Обзор | роль, число тарифов и платежей | `GET /api/admin/overview` |
| Тарифы | имя, цена, включён | `GET /api/admin/plans` |
| Платежи | id, сумма, валюта, статус | `GET /api/admin/payments` |
| Мониторинг | очищенный статус узлов | `GET /api/admin/remnawave/monitoring` |
| Платформа | нарушения, агенты (имя и CPU), страны | `GET /api/admin/platform/summary` |
| Платформа | ограничить или снять | `POST /api/admin/platform/violations/{id}/review` с `restrict` или `clear` |
| Поддержка | ответ | `POST /api/admin/support/tickets/{id}/reply` с полем `reply` |

Код 2FA короче 6 символов на сервер не отправляется: пустое поле означает вход без OTP. Если у администратора включена 2FA, сервер отвечает 401, пока код не введён.

Сводка платформы не содержит токен агента, хеш ключа API и секрет webhook.

## Buyer functions (English)

Sign-in and registration use email and a password of at least 8 characters (`POST /api/auth/login`, `POST /api/auth/register`). Overview reads the wallet, referral code and subscription (`GET /api/me/dashboard`). Plans pay through `POST /api/payments/create` or debit the wallet through `POST /api/me/wallet/spend`; both send `Idempotency-Key`. The builder sends the first enabled device, traffic and day option ids. Servers show name, country, status and online users from `GET /api/me/servers`. Connection copies the subscription link, shows the six device guides from `GET /api/me/connection-info`, and starts a trial with `POST /api/me/trial`. Support creates a ticket. The language chip reloads the catalog and sends `Accept-Language`.

The payment provider comes from `GET /api/public/config`: `sandbox` wins when it is listed, otherwise the first provider is used. The client filters every node down to `name`, `country`, `status` and `users_online`, and replaces a host-like name with `node`.

## Administrator functions (English)

Sign-in posts email, password and a 2FA code only when the field is not blank. Overview shows the role and the plan and payment counts. Plans, payments and monitoring are read-only lists. Platform loads violations, agent name and CPU, and country counts, then posts `restrict` or `clear`. Support posts a reply. The platform summary does not include the agent token, the API key hash or the webhook secret.

## Покупатель и администратор в 2.10.0

Покупатель видит QR подписки, кнопки Happ, v2rayNG и Streisand, расход и лимит, список устройств с отзывом, подарочный код и пополнение. Администратор включает тариф, открывает карточку платежа и видит, устарел ли агент. Сохранённый токен закрыт биометрией или PIN. Каждый запрос несёт `X-Shop-Time` и `X-Shop-Proof`.

The buyer sees the subscription QR, Happ, v2rayNG and Streisand buttons, usage and limit, a device list with revoke, a gift code and a top-up. The administrator enables a plan, opens a payment card and sees whether an agent is stale. A saved token is locked with biometrics or the device PIN. Every call sends `X-Shop-Time` and `X-Shop-Proof`.

## Сборка

Android: релиз **2.10.0** прикладывает два release APK: `remnawave_vpn_shop_android_user_2_10_0.apk` и `remnawave_vpn_shop_android_admin_2_10_0.apk`. Рядом лежит `.sha256`. Релиз **2.9.0** прикладывал debug APK `remnawave_vpn_shop_android_user_2_9_0.apk` и `remnawave_vpn_shop_android_admin_2_9_0.apk`. Перед установкой 2.10.0 debug-пакет удаляют один раз. Повторная сборка release: задайте `ANDROID_KEYSTORE`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS` и `ANDROID_KEY_PASSWORD`. Без keystore скрипт собирает debug. Команда:

```bash
ANDROID_HOME=$HOME/android-sdk GRADLE_BIN=$HOME/gradle-8.10.2/bin/gradle bash scripts/build-android-apk.sh /tmp/apk
```

Нужны Android SDK 35, build-tools 35.0.0 и Gradle 8.10.2. С ключом скрипт вызывает `:app:assembleRelease`, иначе `:app:assembleDebug`, в `mobile/android-user` и `mobile/android-admin` (AGP 8.7, Kotlin 2.0, compileSdk 35, minSdk 26, versionName `2.10.0`, исторический versionName `2.9.0` оставлен комментарием в Gradle). Cleartext в `network_security.xml` разрешён только для трёх локальных хостов. Пакет 2.10.0 подписан release-ключом и ставится вручную. Для Google Play подпись задаёт владелец. Закрытый ключ в git не коммитится.

iOS: откройте `mobile/ios-user/VpnShopUser.xcodeproj` или `mobile/ios-admin/VpnShopAdmin.xcodeproj` в Xcode 15+ на macOS (iOS 16, Swift 5, MARKETING_VERSION `2.10.0`, предыдущая версия интерфейса `2.9.0`). В проекте `CODE_SIGNING_ALLOWED = NO`, чтобы дерево собиралось без команды; для устройства подпись настраивается в Xcode. `NSAllowsLocalNetworking` разрешает локальный HTTP. IPA появляется после Product → Archive в Xcode. На Linux Xcode нет, поэтому релиз IPA не содержит.

Android: the **2.10.0** GitHub release attaches `remnawave_vpn_shop_android_user_2_10_0.apk` and `remnawave_vpn_shop_android_admin_2_10_0.apk` with `.sha256` files. The **2.9.0** release attached `remnawave_vpn_shop_android_user_2_9_0.apk` and `remnawave_vpn_shop_android_admin_2_9_0.apk`. Rebuild with `scripts/build-android-apk.sh` (SDK 35, Gradle 8.10.2, `assembleRelease` when `ANDROID_KEYSTORE` is set, otherwise `assembleDebug`). iOS: open the `.xcodeproj` in Xcode on macOS. `CODE_SIGNING_ALLOWED = NO` lets the tree compile without a team; a device build needs a signing team. The IPA is produced by Xcode Archive. This Linux host has no Xcode, so the release has no IPA.

## Проверенные ошибки 2.9.0

- Платёжная ссылка Android сравнивалась по префиксу `http://localhost`. Адрес `http://localhost.example` проходил бы эту проверку. Теперь URL разбирается, хост сравнивается целиком, логин в адресе отклоняется.
- `localHttpHosts` в iOS-приложении покупателя был `private` в другом файле, и экран оплаты не собирался в Xcode. Константа доступна модулю, экран оплаты её видит.

## Проверенные ошибки клиентов

- JSONSerialization на iOS отдаёт числа как `NSNumber`. Приведение `as? Int` не видело id тарифа, пункта конструктора, нарушения и тикета, поэтому оплата, пробный период, ограничение и ответ поддержки не уходили. Чтение идёт через `jsonInt`.
- Словарь инструкций `platforms` приходит как `[String: Any]`. Приведение к `[String: String]` оставляло экран пустым.
- Пароль вводился открытым текстом. Поля пароля закрыты.
- После входа список данных оставался пустым, пока пользователь не нажимал загрузку. Сохранённая сессия теперь обновляет экраны сама.
- Обзор Android-админки подписывал роль словом «версия». Строка показывает роль.
- iOS-админка не показывала агентов, хотя сводка их содержит. Список агентов добавлен.

JSONSerialization on iOS returns numbers as `NSNumber`. An `as? Int` cast missed plan, option, violation and ticket ids, so payment, trial, restrict and support reply never ran. Those values are read with `jsonInt`. The guides dictionary is read as `[String: Any]`. Password fields are masked. A saved session refreshes itself. The Android admin overview labels the role as a role. The iOS admin lists agents from the platform summary.
