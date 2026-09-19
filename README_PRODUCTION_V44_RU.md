# Remnawave VPN Shop V44 Enterprise

Production release с Enterprise-центром, мультиустройствами, Trial, Campaign Manager, Rules Engine и 24/7 monitoring.

**Версия:** 44.1.0-enterprise  
**Migration head:** 0022_enterprise_suite  
**Автотесты:** 112 passed

## Быстрый старт

1. Скопировать `.env.example` в production `.env` и заполнить secrets.
2. Установить/проверить Docker Compose.
3. Запустить preflight.
4. Выполнить миграции.
5. Проверить `/health`.
6. Настроить Telegram ID администраторов и MFA.
7. Настроить staging E2E.
8. Только после реального полного E2E открыть production payment gate.

Полная документация: `DOCUMENTATION_V44_RU.md`.

## Enterprise

В админ-панели добавлен раздел **Enterprise V44**:

- 24/7 мониторинг;
- Campaign Manager;
- Rules Engine;
- мультиустройства;
- Trial;
- существующие Smart Payment Router, Anti-Fraud, CRM, Analytics, Node Manager, Support и Disaster Recovery.

## Важное

Production payment gate остаётся fail-closed. Успешное создание тестового платежа само по себе не открывает реальные платежи.
