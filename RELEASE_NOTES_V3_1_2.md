# Release notes 3.1.2

## Русский

Аудит 3.1.2 закрывает утечки учётных данных VPN и текста исключений в ответах панели. Схема остаётся `0038_v2_6_0_platform`. Новых APK и IPA нет: покупатель Android остаётся **2.10.0**, администратор Android — **2.12.0**. Production gate по-прежнему требует строку `FULL_E2E_PASS`. Сохранение секретов staging и замена `[скрыто]` из **3.1.1** остаются.

### Критические

- Роль `viewer` больше не читает подписку и ключи Remnawave. `GET /api/admin/remnawave/users/{id}/subscription` и `GET /api/admin/remnawave/users/{id}/keys` требуют право `users.keys`. Оно есть у ролей `operator` и `admin`.
- Списки, поток и карточка пользователя Remnawave проходят `redact_remote`. Из ответа убираются ссылка подписки, `shortUuid`, пароли Trojan, VLESS и Shadowsocks и поля с теми же маркерами. Обзор отдаёт только `response.total`, без объекта пользователя.
- Идентификатор пользователя Remnawave принимается строкой, в том числе UUID. Пустая строка, длина больше 80 и символы вне букв, цифр, дефиса и подчёркивания отвечают 400 «Некорректный идентификатор пользователя Remnawave».

### Важные

- Диагностика, задания, резервные копии, здоровье провайдеров, выплаты, мониторы и операции восстановления отдают `error` и `last_error` как `unavailable`. Текст исключения остаётся в журнале процесса.
- Восстановление и тестовое восстановление не возвращают stderr `psql` и `alembic`. Ответ — «Restore failed» или «Migration after restore failed».
- Установка узла по SSH не возвращает вывод `docker compose` и не вкладывает stderr в ответ. Сообщение клиенту: `Remote install failed`.
- `GET /api/admin/audit` в JSON-поле `details` заменяет ключи `error`, `token`, `secret`, `password` и `authorization` на `unavailable`. Произвольный текст, который не является JSON, остаётся.
- Причина возврата в списке и в карточке клиента обрезается перед служебным хвостом с текстом исключения. Статус возврата сохраняется.
- Оповещение в Telegram о сбое планировщика возвратов и о сбое резервной копии не содержит текст исключения. Кнопка запуска копии отвечает «Backup failed», если команда копирования упала.
- Обзор считает тарифы и платежи запросом `COUNT`, а не загрузкой всех строк.

### Что не менялось

- Кнопка **Разрешить реальные платежи** по-прежнему ждёт `passed`, `full_e2e` и `FULL_E2E_PASS` моложе 24 часов. Порядок — раздел 9.15 `INSTRUCTION.md`.
- Пошаговая установка — `INSTALL_STEPS.md`. Вопросы установщика те же, что в **3.1.1**.
- Лицензия — Remnawave VPN Shop Proprietary License 1.0.

## English

The 3.1.2 audit closes leaks of VPN credentials and exception text in panel responses. The schema stays `0038_v2_6_0_platform`. There is no new APK and no IPA: the Android buyer app stays **2.10.0** and the Android administrator app stays **2.12.0**. The production gate still requires the line `FULL_E2E_PASS`. Staging-secret preservation and the `[скрыто]` replacement from **3.1.1** remain.

### Critical

- Role `viewer` no longer reads a Remnawave subscription or connection keys. `GET /api/admin/remnawave/users/{id}/subscription` and `GET /api/admin/remnawave/users/{id}/keys` require `users.keys`. Roles `operator` and `admin` have that permission.
- Remnawave user lists, the stream, and the user card pass through `redact_remote`. The response drops the subscription URL, `shortUuid`, Trojan, VLESS, and Shadowsocks passwords, and fields that carry the same markers. Overview returns only `response.total`, without a user object.
- A Remnawave user id is accepted as a string, including a UUID. An empty string, a value longer than 80 characters, or a character outside letters, digits, hyphen, and underscore answers 400 «Некорректный идентификатор пользователя Remnawave».

### Important

- Diagnostics, jobs, backups, provider health, payouts, monitors, and recovery operations return `error` and `last_error` as `unavailable`. The exception text stays in the process log.
- Restore and test-restore do not return `psql` or `alembic` stderr. The response is “Restore failed” or “Migration after restore failed”.
- SSH node install does not return `docker compose` output and does not embed stderr in the response. The client message is `Remote install failed`.
- `GET /api/admin/audit` replaces JSON keys `error`, `token`, `secret`, `password`, and `authorization` inside `details` with `unavailable`. Free text that is not JSON stays.
- A refund reason in the list and on the customer card is cut before the operational tail that carried exception text. The refund status stays.
- The Telegram alert for a refund-scheduler failure and for a backup failure does not include the exception text. The backup button answers “Backup failed” when the copy command fails.
- Overview counts plans and payments with `COUNT` instead of loading every row.

### Unchanged

- **Разрешить реальные платежи** (Allow live payments) still waits for `passed`, `full_e2e`, and `FULL_E2E_PASS` younger than 24 hours. The order is section 9.15 of `INSTRUCTION.md`.
- The step-by-step install is `INSTALL_STEPS.md`. The installer prompts are the same as in **3.1.1**.
- The license remains Remnawave VPN Shop Proprietary License 1.0.
