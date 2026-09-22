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

## Language

Кнопка языка в шапке переключает русский и английский. Выбор хранится в `localStorage` (`rw_lang`). Русские строки остаются в `src/main.tsx`, английские подставляются словарём `src/i18n.tsx` после отрисовки. Пока выбора нет, язык берётся из браузера. Серверный `DEFAULT_LANGUAGE` задаёт запасной язык Mini App и бота.

The header language button switches Russian and English. The choice is stored in `localStorage` (`rw_lang`). Russian strings stay in `src/main.tsx`; English is applied after render from `src/i18n.tsx`.
