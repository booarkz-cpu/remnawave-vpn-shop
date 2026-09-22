# Remnawave VPN Shop 2.8.0

Предыдущий релиз **2.7.0** добавил приложения Android и iOS. **2.8.0** даёт администратору управление текстами этих приложений и общим логотипом кабинета и приложений.

The previous release **2.7.0** added the Android and iOS apps. **2.8.0** lets an administrator edit the app texts and the logo shared by the user cabinet and the apps.

## Что вошло

- Вкладка админки **Приложения**. Четыре карточки: Android и iOS для покупателя, Android и iOS для администратора. У каждой название и текст на русском и английском, ссылка `https://` и переключатель показа.
- `GET /api/public/apps` отдаёт логотип и только включённые карточки покупателя. Карточки администратора и выключенные карточки в этот ответ не входят.
- `GET /api/admin/apps` и `PUT /api/admin/apps` читают и сохраняют все четыре карточки. Запись требует право `manage_content`.
- `POST /api/admin/apps/logo` и `DELETE /api/admin/apps/logo` меняют логотип. Файл перекодируется в PNG. В ответ и в кабинет попадает только путь `/media/<имя>`.
- Личный кабинет показывает логотип в шапке и блок «Приложения» с текстами на языке кабинета. Ссылка открывается только если она начинается с `https://`.
- Приложения Android и iOS запрашивают тот же каталог и рисуют логотип, если путь безопасный. Редиректы при загрузке картинки не следуют.
- Схема базы не менялась. Голова миграций остаётся `0038_v2_6_0_platform`. Настройки лежат в `app_settings`: `mobile_apps` и `client_logo`.

## English

The admin **Приложения** tab edits four cards: Android and iOS for the buyer, Android and iOS for the administrator. Each card has a Russian title, an English title, both descriptions, an `https://` link and a visibility switch.

`GET /api/public/apps` returns the logo and the enabled buyer cards. Administrator cards and disabled cards stay out of that response. Saving the catalog requires `manage_content`. The logo upload is re-encoded to PNG and stored as `/media/<name>`.

The user cabinet shows the logo in the header and an Apps block in the selected language. A link opens only when it starts with `https://`. The Android and iOS apps load the same catalog and draw the logo when the media path is safe. They do not follow redirects while downloading the image.

The database migration head stays `0038_v2_6_0_platform`. The settings are `mobile_apps` and `client_logo` in `app_settings`.

## Лицензия

Лицензия прежняя: Remnawave VPN Shop Proprietary License 1.0 (`LicenseRef-Proprietary`). Файл `LICENSE` покрывает веб-кабинет, админку и приложения Android и iOS.
