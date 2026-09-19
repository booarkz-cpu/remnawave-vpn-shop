# Remnawave VPN Shop V12 — Release Notes

## Главное
- Версия API: `12.0`.
- Installer теперь открывает только необходимые входящие порты: 22/TCP, 80/TCP, 443/TCP и 443/UDP; режим UFW — strict.
- UFW по умолчанию работает в строгом режиме: inbound разрешены только SSH, 80/TCP, 443/TCP и 443/UDP.

## Критические исправления
- Исправлена ошибка RBAC V11: backup endpoints требовали несуществующее permission `admin`, поэтому полноценный backup/download/config были недоступны. Теперь используется `manage_admins`.
- Исправлена async-функция `user_from_token`: ранее она возвращала coroutine вместо пользователя.
- Усилена защита платежей: блокировка строки пользователя на время fulfillment не даёт параллельным успешным webhook создать два Remnawave-пользователя для одного клиента.
- Промокоды блокируются на уровне БД-транзакции при проверке лимита использования, что снижает риск превышения `usage_limit` при гонке запросов.
- Backup download/delete защищены от path traversal через нормализацию и проверку имени файла.

## Дополнительная защита
- Trusted Host validation для API/Admin/App доменов.
- Rate limiting для Telegram/Yandex auth, payment creation и promo validation.
- Ограничение HTTP request body до 12 MiB.
- `Cache-Control: no-store` для admin/auth API.
- Ограничена память in-process rate limiter от бесконечного роста.
- SSH hardening без изменения способа аутентификации, чтобы не запереть владельца на свежем VDS.
- Сохраняются MFA/TOTP, RBAC, security headers, fail2ban, unattended-upgrades, private DB/backend ports, encrypted backups и no-new-privileges из V11.
