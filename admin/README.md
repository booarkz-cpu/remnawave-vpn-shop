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

## 3.1.3

Установщик 3.1.3 не меняет панель. Команда `curl | bash` на сервере снова задаёт вопросы с терминала SSH.

Installer 3.1.3 does not change the panel. `curl | bash` on the server asks questions from the SSH terminal again.

## 3.1.2

Обзор показывает только общее число пользователей Remnawave. Карточка пользователя не содержит ссылку подписки и пароли протоколов. Подписка и ключи открываются ролям с правом `users.keys`. Поля ошибок в заданиях, копиях и состоянии показывают `unavailable`. Журнал аудита не отдаёт текст исключения из JSON.

Overview shows only the Remnawave user total. The user card omits the subscription URL and protocol passwords. The subscription and keys open for roles with `users.keys`. Error fields on jobs, backups, and status show `unavailable`. The audit log does not return exception text from JSON.

## 3.1.1

Вкладка **Проверка тестового контура** требует флажок **Подтверждаю sandbox-ключи**. Пустое поле секрета, Shop ID или Merchant ID при повторном сохранении оставляет записанное значение. Журнал показывает строку `[CHECKOUT]`. Кнопка **Разрешить реальные платежи** на вкладке **Безопасность** включает gate после `FULL_E2E_PASS` не старше 24 часов. Порядок — раздел 9.15 `INSTRUCTION.md`.

**Проверка тестового контура** (Staging checks) requires **Подтверждаю sandbox-ключи** (I confirm these are sandbox keys). A blank secret, Shop ID, or Merchant ID on a later save keeps the stored value. The log shows a `[CHECKOUT]` line. **Разрешить реальные платежи** (Allow live payments) on **Безопасность** (Security) enables the gate after `FULL_E2E_PASS` younger than 24 hours. The order is section 9.15 of `INSTRUCTION.md`.

## 3.1.0

Карточка приложения показывает контрольную сумму SHA-256, когда файл загружен. Публичный список тарифов её не касается: идентификатор профиля Remnawave в ответе покупателя отсутствует.

An app card shows the SHA-256 checksum when a file is uploaded. The public plan list is separate: the buyer response does not include the Remnawave profile id.

## 3.0.1

Повторная оплата с баланса в течение 30 секунд не создаёт второе списание. Загрузка пакета по-прежнему проверяет `manage_content` до чтения файла.

A second wallet payment within 30 seconds does not create another debit. A package upload still checks `manage_content` before the file is read.

## 3.0.0-realise

Загрузка APK или IPA на карточку принимает файл до 80 МБ при `Content-Length`. Сессия без `manage_content` получает отказ до чтения файла.

An APK or IPA upload accepts a file up to 80 MB when `Content-Length` is set. A session without `manage_content` is rejected before the file is read.

## Скачивание / Downloads

Вкладка **Приложения** загружает APK и IPA, меняет тексты карточек и показывает ссылку на приложение администратора. Кабинет покупателя получает ссылку только на включённые карточки покупателя.

The **Приложения** tab uploads an APK or IPA, edits the card texts and shows the administrator app link. The buyer cabinet receives a link only for enabled buyer cards.

## Рассылка / Broadcast

Раздел **Маркетинг** ставит HTML-рассылку в очередь бота. Аудитория: все с Telegram, активная подписка или без активной подписки. Кнопка и картинка — HTTPS. Повтор продолжает счётчик. Подробности — `INSTRUCTION.md`, раздел 9.10.

The **Marketing** section queues an HTML broadcast for the bot. The audience is everyone with Telegram, an active subscription, or no active subscription. A button and an image use HTTPS. Retry continues the counter. Details are in `INSTRUCTION.md`, section 9.10.
