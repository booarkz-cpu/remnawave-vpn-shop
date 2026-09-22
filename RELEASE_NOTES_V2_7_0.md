# Remnawave VPN Shop 2.7.0

Предыдущий релиз **2.6.0** закрыл платформу антиабьюза, агент узла и проприетарную лицензию. **2.7.0** добавляет четыре отдельных приложения: Android и iOS для покупателя и Android и iOS для администратора, с переключением русского и английского.

The previous release **2.6.0** added the abuse platform, the node agent and the proprietary license. **2.7.0** adds four separate apps: Android and iOS for the buyer, and Android and iOS for the administrator, with a Russian and English switch.

## Что вошло

- `mobile/android-user` и `mobile/ios-user`: вход и регистрация по email, обзор, тарифы, конструктор, серверы, ссылка подписки и инструкции, пробный период, поддержка.
- `mobile/android-admin` и `mobile/ios-admin`: вход с необязательным кодом 2FA, обзор, тарифы, платежи, мониторинг Remnawave, разбор нарушений, агенты, страны, ответ в поддержку.
- Общий вид: тёмная схема Material и акцент `#00E5C0`.
- Каталоги `mobile/l10n/user.json` и `mobile/l10n/admin.json`. Ключи ru и en совпадают, копии в приложениях побайтные.
- `backend/app/mobile_auth.py`: токен попадает в JSON только при заголовке `X-Shop-Client` из списка `android-user`, `android-admin`, `ios-user`, `ios-admin`. Веб-вход cookie не меняет и токен в JSON не кладёт.
- `GET /api/me/connection-info` выбирает английские инструкции, если `Accept-Language` начинается с `en`. Сохранённые администратором тексты по-прежнему перекрывают значения по умолчанию.
- Веб-админка, кабинет и Mini App переводят `aria-label` и строку «Онлайн N из M».
- Схема базы не менялась. Голова миграций остаётся `0038_v2_6_0_platform`.

## Границы версии

- В архиве релиза исходники приложений. Готовых APK и IPA нет: их собирают Android Studio и Xcode. В среде публикации нет Android SDK и компилятора Swift.
- Приложения не ставят VPN-профиль сами. Покупатель копирует ссылку подписки и открывает её в своём VPN-клиенте по инструкции.
- Оплата уходит в браузер по https-ссылке провайдера. Локальный http разрешён только для `localhost`, `127.0.0.1` и `10.0.2.2`.
- Админские приложения читают тарифы и платежи и не создают тарифы, ключи API и webhook.
- Лицензия прежняя: Remnawave VPN Shop Proprietary License 1.0. Текст в `LICENSE` явно включает приложения Android и iOS.

## English

The buyer apps sign in and register by email, then show the overview, plans, the tariff constructor, servers, the subscription link and device guides, a trial and support. The admin apps sign in with an optional 2FA code, then show the overview, plans, payments, Remnawave monitoring, violation review, agents, countries and support replies.

`mobile_auth.py` returns `access_token` only when `X-Shop-Client` is one of the four client names. Web login still uses the HttpOnly cookie and does not put the token in JSON. The database migration head stays `0038_v2_6_0_platform`.

The release archive contains application source. It does not contain an APK or an IPA. The apps do not install a VPN profile; the buyer copies the subscription link. Admin apps do not create plans, API keys or webhooks. The license remains the Remnawave VPN Shop Proprietary License 1.0, and `LICENSE` names the Android and iOS apps.
