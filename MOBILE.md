# Мобильные приложения 2.7.0 / Mobile apps 2.7.0

Четыре отдельных клиента магазина: Android и iOS для покупателя, Android и iOS для администратора. Общий вид — тёмная схема Material Design и акцент Web 3.0 `#00E5C0`. В каждом приложении есть переключатель **RU / EN**.

Four separate shop clients: Android and iOS for the buyer, Android and iOS for the administrator. The shared look is a dark Material Design scheme with the Web 3.0 accent `#00E5C0`. Each app has a **RU / EN** language switch.

Русский и English живут в одном каталоге на роль: `mobile/l10n/user.json` и `mobile/l10n/admin.json`. Копии лежат в assets Android и в бандле iOS и должны совпадать побайтно.

## Лицензия

Приложения входят в Remnawave VPN Shop и покрываются **Remnawave VPN Shop Proprietary License 1.0** (`SPDX-License-Identifier: LicenseRef-Proprietary`). Полный текст — корневой файл `LICENSE`. Краткая отсылка — `mobile/LICENSE`.

The apps are part of Remnawave VPN Shop and are covered by the Remnawave VPN Shop Proprietary License 1.0. The full text is the root `LICENSE` file. `mobile/LICENSE` is a short pointer.

## Состав

| Приложение | Каталог | Идентификатор | `X-Shop-Client` | User-Agent |
| --- | --- | --- | --- | --- |
| Android, покупатель | `mobile/android-user` | `shop.remnawave.user` | `android-user` | `RemnawaveShop-Android-User/2.7.0` |
| Android, администратор | `mobile/android-admin` | `shop.remnawave.admin` | `android-admin` | `RemnawaveShop-Android-Admin/2.7.0` |
| iOS, покупатель | `mobile/ios-user` | `shop.remnawave.user` | `ios-user` | `RemnawaveShop-iOS-User/2.7.0` |
| iOS, администратор | `mobile/ios-admin` | `shop.remnawave.admin` | `ios-admin` | `RemnawaveShop-iOS-Admin/2.7.0` |

User-Agent должен оставаться одинаковым между входом и следующими запросами: сессия привязана к нему, смена строки отзывает сессию.

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

## Сборка

Android: откройте `mobile/android-user` или `mobile/android-admin` в Android Studio (AGP 8.7, Kotlin 2.0, compileSdk 35, minSdk 26) и соберите debug или release. Gradle Wrapper в репозиторий не вложен. Cleartext в `network_security.xml` разрешён только для трёх локальных хостов.

iOS: откройте `mobile/ios-user/VpnShopUser.xcodeproj` или `mobile/ios-admin/VpnShopAdmin.xcodeproj` в Xcode 15+ (iOS 16, Swift 5). В проекте `CODE_SIGNING_ALLOWED = NO`, чтобы дерево собиралось без команды; для устройства подпись настраивается в Xcode. `NSAllowsLocalNetworking` разрешает локальный HTTP.

На этой среде сборки нет Android SDK, kotlinc и Swift, поэтому бинарные APK и IPA в релиз не входят. Контракты исходников проверяет `tests/test_v270_mobile_apps.py`.

Android: open `mobile/android-user` or `mobile/android-admin` in Android Studio and assemble a debug or release build. The Gradle wrapper JAR is not committed. iOS: open the `.xcodeproj` in Xcode. Signing is disabled in the project file so the tree can be built without a team; a device build needs a signing team in Xcode. This environment has no Android SDK and no Swift compiler, so the GitHub release does not contain an APK or an IPA.

## Проверенные ошибки клиентов

- JSONSerialization на iOS отдаёт числа как `NSNumber`. Приведение `as? Int` не видело id тарифа, пункта конструктора, нарушения и тикета, поэтому оплата, пробный период, ограничение и ответ поддержки не уходили. Чтение идёт через `jsonInt`.
- Словарь инструкций `platforms` приходит как `[String: Any]`. Приведение к `[String: String]` оставляло экран пустым.
- Пароль вводился открытым текстом. Поля пароля закрыты.
- После входа список данных оставался пустым, пока пользователь не нажимал загрузку. Сохранённая сессия теперь обновляет экраны сама.
- Обзор Android-админки подписывал роль словом «версия». Строка показывает роль.
- iOS-админка не показывала агентов, хотя сводка их содержит. Список агентов добавлен.

JSONSerialization on iOS returns numbers as `NSNumber`. An `as? Int` cast missed plan, option, violation and ticket ids, so payment, trial, restrict and support reply never ran. Those values are read with `jsonInt`. The guides dictionary is read as `[String: Any]`. Password fields are masked. A saved session refreshes itself. The Android admin overview labels the role as a role. The iOS admin lists agents from the platform summary.
