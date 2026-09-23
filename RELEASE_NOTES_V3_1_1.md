# Remnawave VPN Shop 3.1.1

## Русский

Версия **3.1.1** — сервер, панель и документация. Схема остаётся `0038_v2_6_0_platform`. Новых APK и IPA нет: покупатель Android остаётся **2.10.0**, администратор Android остаётся **2.12.0**. Предыдущий релиз — **3.1.0**.

- Повторное сохранение вкладки **Проверка тестового контура** больше не стирает уже записанные секреты. Пустое поле оставляет прежнее зашифрованное значение. Сравнение с production-ключами выполняется по объединённым значениям. Пустой токен Remnawave по-прежнему отвечает 400 «Укажите токен Remnawave для staging».
- Сохранение по-прежнему выключает production gate и выпускает новый runner token.
- Журнал раннера печатает `[CHECKOUT]` и https-адрес оплаты. Статус `awaiting_checkout` gate не открывает.
- Перед записью журнала секреты длиннее 7 символов заменяются на `[скрыто]`. Shop ID и Merchant ID в строке не заменяются, чтобы адрес оплаты оставался открываемым.
- Образ `backend` содержит `curl`: раннер `/app/staging-e2e.sh` вызывает его для `/health`, Remnawave и локального создания платежа.
- Флажок **Подтверждаю sandbox-ключи** обязателен. Панель больше не отправляет подтверждение сама.
- Пошаговая установка — `INSTALL_STEPS.md`. Порядок в панели — раздел 9.15 `INSTRUCTION.md`.

Кнопка **Разрешить реальные платежи** включает gate, когда статус `passed`, поле `full_e2e` истинно и `finished_at` моложе 24 часов. Раннер пишет `FULL_E2E_PASS` только после наблюдаемой цепочки checkout → webhook → fulfillment → повторный webhook → refund. Создание платежа само по себе эту строку не печатает.

## English

Version **3.1.1** is a server, panel, and documentation release. The schema stays `0038_v2_6_0_platform`. There is no new APK and no IPA: the Android buyer app stays **2.10.0** and the Android administrator app stays **2.12.0**. The previous release is **3.1.0**.

- Saving **Проверка тестового контура** (Staging checks) again keeps secrets already stored. A blank field leaves the previous encrypted value. The production-credential comparison uses the merged values. An empty Remnawave token still answers 400 «Укажите токен Remnawave для staging».
- A save still turns the production gate off and mints a new runner token.
- The runner log prints `[CHECKOUT]` and the https payment URL. Status `awaiting_checkout` does not open the gate.
- Before the log is stored, secrets of 8 characters or more are replaced with `[скрыто]`. Shop ID and Merchant ID stay in the line so the payment URL remains openable.
- The `backend` image includes `curl`, which `/app/staging-e2e.sh` uses for `/health`, Remnawave, and the local payment create.
- The checkbox **Подтверждаю sandbox-ключи** (I confirm these are sandbox keys) is required. The panel no longer sends the confirmation by itself.
- The step-by-step install is `INSTALL_STEPS.md`. The panel order is section 9.15 of `INSTRUCTION.md`.

**Разрешить реальные платежи** (Allow live payments) enables the gate when the status is `passed`, `full_e2e` is true, and `finished_at` is younger than 24 hours. The runner writes `FULL_E2E_PASS` after the observed chain checkout → webhook → fulfillment → duplicate webhook → refund. Payment creation alone does not print that line.
