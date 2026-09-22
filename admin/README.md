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

## 3.0.0-realise

Загрузка APK или IPA на карточку принимает файл до 80 МБ при `Content-Length`. Сессия без `manage_content` получает отказ до чтения файла.

An APK or IPA upload accepts a file up to 80 MB when `Content-Length` is set. A session without `manage_content` is rejected before the file is read.

## Скачивание / Downloads

Вкладка **Приложения** загружает APK и IPA, меняет тексты карточек и показывает ссылку на приложение администратора. Кабинет покупателя получает ссылку только на включённые карточки покупателя.

The **Приложения** tab uploads an APK or IPA, edits the card texts and shows the administrator app link. The buyer cabinet receives a link only for enabled buyer cards.

## Рассылка / Broadcast

Раздел **Маркетинг** ставит HTML-рассылку в очередь бота. Аудитория: все с Telegram, активная подписка или без активной подписки. Кнопка и картинка — HTTPS. Повтор продолжает счётчик. Подробности — `INSTRUCTION.md`, раздел 9.10.

The **Marketing** section queues an HTML broadcast for the bot. The audience is everyone with Telegram, an active subscription, or no active subscription. A button and an image use HTTPS. Retry continues the counter. Details are in `INSTRUCTION.md`, section 9.10.
