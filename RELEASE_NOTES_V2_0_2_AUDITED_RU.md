# Release 2.0.2-audited — исправления критического аудита

Дата: 2026-09-14

## Что исправлено

### C-01 — Telegram login: отсутствовал `Request`
`/api/auth/telegram` использовал `request` для создания server-side user session и audit IP, но параметр `Request` отсутствовал в сигнатуре. В runtime успешная Telegram-аутентификация падала с `NameError`.

**Исправление:** `request: Request` добавлен в endpoint.

### C-02 — Yandex exchange: отсутствовал `Request`
`/api/auth/exchange` также использовал `request` для session metadata и audit IP без параметра в сигнатуре.

**Исправление:** `request: Request` добавлен в endpoint.

### C-03 — release scripts потеряли executable bit
`install.sh`, `scripts/build-release.sh` и `scripts/staging-e2e.sh` были распакованы как обычные файлы. Существующие regression tests это обнаружили.

**Исправление:** executable mode восстановлен для release/operations shell scripts; добавлен отдельный regression test.

### C-04 — CI не мог валидировать Compose на чистом runner
`docker compose config` требовал обязательные переменные из production `.env`, которого нет в CI.

**Исправление:** CI создаёт минимальный безопасный `.env` только для синтаксической Compose-проверки.

## Проверка

- `pytest`: **270 passed**
- `python -m compileall -q backend`: PASS
- AST-проверка использования `request` без параметра: PASS
- `bash -n install.sh deploy/*.sh scripts/*.sh`: PASS
- executable mode release scripts: PASS

## Важное ограничение

Live staging E2E с реальными sandbox credentials, Telegram, платёжными провайдерами и Remnawave в этой среде не выполнялся. Поэтому этот релиз не заменяет обязательную production/staging acceptance-проверку.

## Совместимость

Миграционный head остаётся:

`0032_v2_0_0_product_features`

Отдельной миграции для исправлений 2.0.1 не требуется: исправления относятся к runtime/release tooling.


### C-05 — рассинхронизация runtime version
`backend/app/main.py` сообщал `2.0.0-realise`, хотя артефакт и release tooling были `2.0.2-audited`. Runtime version обновлена; добавлена автоматическая проверка release identity.

### Повторная верификация
После исправления выполнен полный regression suite: **271 passed**.
