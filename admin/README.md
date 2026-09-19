# Remnawave VPN Shop — Admin Panel

## Branding

В разделе **Брендинг панели** администратор с permission `manage_content` может задать:

- название веб-панели;
- логотип PNG/JPEG/WEBP;
- favicon PNG/JPEG/WEBP;
- тему по умолчанию: светлая или тёмная.

Изображения проходят bounded upload, декодирование и повторное кодирование в PNG на сервере. Исходное имя файла не используется для storage.

## Theme

Тема переключается кнопкой в верхней панели. Выбор пользователя хранится локально в браузере; server-side `theme_default` используется как default для новых/очищенных browser sessions.
