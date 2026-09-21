# Security / Безопасность — Remnawave VPN Shop 2.2.1

Граница доверия: браузер или Telegram → Caddy → API → PostgreSQL, Redis, Remnawave и платёжные провайдеры. PostgreSQL и Redis наружу не публикуются.

Trust boundary: browser or Telegram → Caddy → API → PostgreSQL, Redis, Remnawave and the payment providers. PostgreSQL and Redis are not published to the host network.

## Аутентификация

- Администратор: пароль scrypt, необязательный TOTP, коды восстановления, JWT только вместе с записью `AdminSession`.
- Сессия администратора живёт в HttpOnly cookie, привязана к User-Agent, гаснет через 15 минут простоя и не дольше абсолютного срока токена.
- Покупатель: проверенный Telegram initData или опциональный Yandex ID. Cookie `rw_user` — HttpOnly.
- Мутации с cookie требуют заголовок `X-CSRF-Token`, равный cookie `rw_csrf`. Вебхуки и первичный вход из этого правила исключены.
- RBAC: `viewer`, `operator`, `admin`. Недостаточное право отвечает 403.

## Платежи

- Намерение платежа записывается до вызова провайдера. Повтор с тем же `Idempotency-Key` не создаёт второе списание.
- YooKassa: вебхук отклоняется, если `YOOKASSA_WEBHOOK_IP_ALLOWLIST` пуст или IP отправителя не входит в список. Пустой список больше не означает «принять всех».
- После вебхука API сам читает платёж у провайдера и сверяет статус, сумму, валюту и `order_id`. Текст вебхука не является доказательством оплаты.
- Platega: заголовки магазина. RollyPay: HMAC и окно timestamp 5 минут.
- Возврат идемпотентен по ключу `refund-{payment_id}`. Отзыв VPN не выполняется, если есть более новая успешно выданная оплата.
- Боевые платежи выключены, пока администратор не включит production gate после staging E2E. Staging не читает production-секреты провайдеров.

## Сеть и файлы

- Исходящие запросы к платёжным API идут через DNS-pinned клиент: адрес проверяется на публичность, соединение открывается на проверенный IP, TLS сохраняет исходное имя. Редиректы выключены, `trust_env=False`.
- Загрузка изображений ограничена типом, сигнатурой и размером. Файл перекодируется. Удаление старого файла берёт только basename внутри `MEDIA_DIR`, чтобы значение из базы не вышло за каталог через `..`.
- Тело запроса без `Content-Length` читается потоково и обрывается после 12 МиБ. Некорректный `Content-Length` отвечает 400, а не необработанным исключением.
- Каталоги `MEDIA_DIR` (`/data/media`), `BACKUPS_DIR` (`/data/backups`) и `PROJECT_DIR` (`/project`) заданы в конфигурации и совпадают с томами Docker Compose.
- Архив бэкапа открывается только внутри своего каталога. Восстановление требует явного подтверждения.

## Секреты

- `APP_SECRET` не короче 32 символов. Им подписываются JWT и шифруются TOTP, коды восстановления и staging-конфиг.
- `APP_SECRET_PREVIOUS` нужен только на время ротации.
- Метрики закрыты `METRICS_TOKEN`. Публичный OpenAPI выключен.
- В `.env` не храните реальные ключи в git. Пример — `.env.example`.

## Что это не гарантирует

Gate production не заменяет внешнюю проверку провайдера. Панель не включает WebAuthn автоматически: хранилище ключей есть, криптографическая проверка assertion не притворяется включённой 2FA. Живые кассы YooKassa, Platega, RollyPay и боевой Remnawave в этом репозитории не прогоняются.

## English summary

Admin passwords use scrypt. Optional TOTP and recovery codes are encrypted. Sessions are HttpOnly cookies bound to the user agent, with an idle timeout. Cookie mutations require a CSRF header. YooKassa webhooks fail closed without an IP allowlist, and fulfillment still re-reads the provider payment and checks amount, currency and order id. Uploaded media paths are reduced to a basename inside `MEDIA_DIR`. Outbound payment HTTP uses a DNS-pinned client. Chunked bodies are capped at 12 MiB. An invalid `Content-Length` returns HTTP 400. Live payments stay behind the production gate until staging E2E passes. Passkeys are stored but are not presented as active MFA.
