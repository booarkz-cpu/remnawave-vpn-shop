# Remnawave VPN Shop 2.13.0

Лицензия: Remnawave VPN Shop Proprietary License 1.0, файл `LICENSE`. Схема базы: `0038_v2_6_0_platform`. Новой миграции нет.

## Русский

### Что изменилось

В панели, вкладка **Приложения**, появился блок **Скачать приложение администратора**. В личном кабинете у карточек покупателя появились кнопки **Скачать** и **Скачать по ссылке**.

Администратор с правом `manage_content` загружает APK для Android и IPA для iOS, меняет русские и английские тексты, видимость и https-ссылку. Сохранение текстов не удаляет загруженный файл. Выключенная карточка покупателя исчезает из кабинета вместе со ссылкой. Пакет администратора из публичного кабинета не скачивается.

Пакет хранится в каталоге `app-packages` рядом с `MEDIA_DIR`, не в `/media`. Имя файла — 32 шестнадцатеричных символа. В JSON его нет. Размер не больше 80 МБ, начало файла — подпись ZIP. Резервная копия забирает этот каталог, восстановление копирует только безопасные имена `.apk` и `.ipa`.

Приложения Android в исходниках остаются: покупатель **2.10.0**, администратор **2.12.0**. Новый файл в панели заменяет ссылку на скачивание, но не меняет versionName уже установленного APK.

### Проверка

`pytest`, разбор Python, `bash -n` и сборка Vite админки и кабинета. Живые кассы, Remnawave и Xcode на машине сборки не запускались. Сборка Docker входит в CI.

### Установка поверх 2.12.0

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

После обновления откройте **Приложения**, загрузите пакеты и проверьте ссылку в кабинете.

## English

License: Remnawave VPN Shop Proprietary License 1.0, file `LICENSE`. Database schema: `0038_v2_6_0_platform`. There is no new migration.

### What changed

The admin **Приложения** (Apps) tab now has **Скачать приложение администратора** (Download the administrator app). Buyer cards in the user cabinet now have **Скачать** (Download) and **Скачать по ссылке** (Download from link).

An administrator with `manage_content` uploads an APK for Android and an IPA for iOS, and edits the Russian and English text, visibility and https link. Saving the text does not delete an uploaded file. A disabled buyer card leaves the cabinet together with its link. The administrator package cannot be downloaded from the public cabinet.

The package is stored in `app-packages` next to `MEDIA_DIR`, not under `/media`. The file name is 32 hexadecimal characters and is not present in JSON. The size limit is 80 MB and the file must start with a ZIP signature. A backup includes this directory. Restore copies only safe `.apk` and `.ipa` names.

The Android sources stay at buyer **2.10.0** and administrator **2.12.0**. A file uploaded in the panel replaces the download link. It does not change the versionName of an APK that is already installed.

### Check

`pytest`, Python compilation, `bash -n`, and the admin and cabinet Vite builds. Live payment gateways, Remnawave and Xcode were not started on the build machine. The Docker build is part of CI.

### Install over 2.12.0

```bash
sudo bash /opt/vpn-shop/scripts/update-from-github.sh
```

After the update, open **Приложения** (Apps), upload the packages and check the link in the cabinet.
