# Remnawave VPN Shop — полная документация V43

## 1. Назначение

Магазин VPN с Telegram-ботом, Telegram Mini App, Remnawave, PostgreSQL, Redis, очередями фоновых задач, платежами YooKassa/Platega/RollyPay, реферальной системой, админ-панелью и безопасным production payment gate.

## 2. Архитектура

- **Caddy** — единственная внешняя точка HTTP/HTTPS.
- **Backend** — FastAPI API и бизнес-логика.
- **Worker** — фоновые jobs, fulfillment, reconciliation.
- **Bot** — Telegram polling и рассылки.
- **Admin** — React/Vite панель управления.
- **Mini App** — пользовательский Telegram Web App.
- **PostgreSQL** — источник истины.
- **Redis** — locks, rate limits, circuit breaker.

Backend/Admin/Mini App не должны публиковать host ports напрямую.

## 3. Установка

1. Скопировать проект на сервер.
2. Заполнить `.env` на основе `.env.example`.
3. Обязательно задать уникальные секреты.
4. Запустить `./install.sh`.
5. Проверить `./scripts/doctor.sh`.
6. Выполнить миграции.
7. Проверить `/health`.

Никогда не помещайте production credentials в staging-поля.

## 4. Платежи

Production платежи по умолчанию заблокированы.

Требуемая последовательность:

`staging configuration → полный E2E → PASS → admin security step-up → production gate`

Критически важно: создание sandbox-платежа само по себе **не является PASS**.

При неоднозначном timeout создания платежа автоматический переход к другому провайдеру запрещён. Это предотвращает двойное создание заказа.

## 5. Production Gate

Gate хранится как `payments.production_gate`.

Значения:

- `0` — платежи заблокированы;
- `1` — разрешены.

Gate можно включить только при подтверждённом полном E2E и свежем результате. Любое изменение staging configuration сбрасывает gate в `0`.

### Важное ограничение V43

В среде разработки без реального sandbox checkout/webhook/refund нельзя честно установить `FULL_E2E_PASS`. Поэтому gate не следует открывать вручную или подменять статус теста.

## 6. Полный E2E

Полный сценарий должен подтвердить:

1. создание тестового пользователя;
2. создание sandbox payment;
3. checkout;
4. подписанный webhook;
5. проверку суммы/валюты;
6. переход в paid;
7. fulfillment;
8. выдачу/продление VPN в Remnawave;
9. повторный webhook без двойной выдачи;
10. refund;
11. корректное состояние после refund;
12. cleanup.

Результат считается PASS только если все обязательные этапы подтверждены.

## 7. Telegram Bot

В Admin → Content можно управлять:

- названием бота;
- кнопками меню;
- порядком кнопок;
- включением/выключением;
- Web App кнопками;
- HTTPS URL кнопками;
- информационными полями;
- изображением `/start`.

Для Telegram URL используются только HTTPS.

Изображения: JPEG/PNG/WebP, максимум 5 MiB, с проверкой MIME и сигнатуры файла.

## 8. Mini App

Настраиваются:

- заголовок;
- подзаголовок;
- фон;
- главное изображение;
- инструкции;
- до 30 кнопок.

Типы кнопок:

- `url` — HTTPS URL;
- `plans` — переход к тарифам;
- `promo` — установка промокода;
- `field` — переход к информационному полю.

Ссылки и field references валидируются сервером.

## 9. Безопасность админки

- пароль + TOTP;
- Telegram Login запрещён для MFA-admin без дополнительной MFA;
- абсолютный timeout сессии;
- idle timeout;
- User-Agent binding;
- Redis rate limiting;
- CSRF;
- RBAC;
- аудит критических операций;
- step-up для чувствительных действий.

Admin content endpoint никогда не должен возвращать полный `AppSetting`. Секреты выдаются только как boolean status.

## 10. Backup

Backup должен иметь checksum. Перед restore создаётся защитная копия.

`test-restore` восстанавливает архив в отдельную временную PostgreSQL БД, проверяет результат и удаляет временную БД. Production БД не используется.

Если проверка restore не прошла, production maintenance должен оставаться включённым согласно процедуре восстановления.

## 11. Diagnostics

Admin → Operations → Diagnostics проверяет PostgreSQL, Redis и Remnawave.

При degraded состоянии production changes следует остановить до устранения причины.

## 12. Incident Center

Для инцидента указываются severity, category, title и details. Все изменения журналируются Audit Log.

## 13. Feature Flags

Feature flags не являются заменой RBAC и не должны отключать механизмы безопасности. Для каждой функции backend должен проверять соответствующий flag до выполнения операции.

## 14. Release verification

После сборки:

```bash
python -m pytest -q
python -m compileall -q backend
bash -n install.sh deploy/*.sh scripts/*.sh
python -c 'import yaml; yaml.safe_load(open("docker-compose.yml"))'
unzip -t remnawave_vpn_shop_v43_1_production.zip
sha256sum -c remnawave_vpn_shop_v43_production.sha256
```

ZIP не содержит собственного финального SHA manifest, потому что это создало бы self-referential checksum. Manifest поставляется отдельно.

## 15. Rollback

1. Остановить изменение production.
2. Отключить production payments.
3. Зафиксировать incident.
4. Сделать backup текущего состояния.
5. Вернуться на предыдущий проверенный release.
6. Выполнить миграционную процедуру.
7. Проверить health/diagnostics.
8. Повторить staging E2E.
9. Только после PASS вернуть production gate.

## 16. Что нельзя делать

- нельзя включать production payments после одного создания sandbox payment;
- нельзя использовать production credentials в staging;
- нельзя вручную подменять `FULL_E2E_PASS`;
- нельзя открывать backend/Admin ports наружу;
- нельзя хранить секреты в Git/ZIP;
- нельзя использовать HTTP URL для Telegram/Mini App кнопок;
- нельзя возвращать секретные AppSetting через public/admin content API.

## 17. Проверка V43

Release должен считаться готовым только после прохождения локального автоматического набора тестов и реального внешнего sandbox E2E. Автоматические тесты не заменяют внешний checkout/webhook/refund тест.

# V2.0.0

В релиз добавлены Billing Center, subscription lifecycle/grace period, Customer 360, user Security Center с server-side sessions, gift codes, refund dry-run, risk summary и System Health. Критический lifecycle revoke теперь имеет состояние `revoke_pending`, чтобы ошибка Remnawave не превращалась в ложное локальное `expired`.
