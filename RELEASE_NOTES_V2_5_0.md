# Release notes 2.5.0

Предыдущий релиз: 2.4.0. Эта версия не копирует чужой исходный код. Сравнение с публичными описаниями Bedolaga ([remnawave-bedolaga-telegram-bot](https://github.com/BEDOLAGA-DEV/remnawave-bedolaga-telegram-bot) и [bedolaga-cabinet](https://github.com/BEDOLAGA-DEV/bedolaga-cabinet)) использовано только как список идей.

Previous release: 2.4.0. This version does not copy third-party source. The public descriptions of those two repositories were used only as a feature checklist.

## Что добавлено / What was added

- Конструктор тарифа в админке: устройства, трафик (0 = безлимит) и срок в днях, у каждого пункта своя цена. Plan builder in the admin console: devices, traffic (0 = unlimited) and duration in days, each with its own price.
- Покупатель собирает комбинацию в личном кабинете и в Mini App. Цена = база + пункты. Снимок пишется в платёж. The buyer assembles the combination in the cabinet and the Mini App. Price = base + options. The snapshot is stored on the payment.
- Якорный тариф скрыт из каталога. Прямая покупка, пробный период и подарок по его id отклоняются. The anchor plan is hidden from the catalog. Direct purchase, trial and gift of that id are rejected.
- Повтор того же `Idempotency-Key` с другой комбинацией отвечает 409. Reusing the same idempotency key for another combination returns 409.
- Мониторинг Remnawave в админке и отдельный статус серверов для пользователя и без входа. Ответ не содержит адресов, токенов и текста исключения. Admin Remnawave monitoring and a separate server status for signed-in and signed-out users. The payload has no addresses, tokens or exception text.
- Вкладка кабинета `servers`. Cabinet tab kind `servers`.
- Миграция `0037_v2_5_0_tariff_constructor`.
- Документы README, INSTRUCTION, SECURITY, MODULES, FUNCTIONS, INSTALL и чеклист обновлены на русском и английском. Как прогнать проект до релиза без касс: `INSTRUCTION.md`, раздел 9.4, и `scripts/sandbox-e2e.sh`.

## Что сознательно не переносилось / Intentionally not ported

У сравниваемых проектов шире платёжный и маркетинговый контур. В 2.5.0 это не добавлялось, потому что дублировало бы уже работающие YooKassa, Platega, RollyPay и sandbox либо требовало бы отдельных договоров и фискальных интеграций:

- десятки дополнительных касс, Telegram Stars, CryptoBot, Heleket, CloudPayments, Freekassa;
- фискализация;
- конкурсы, ежедневные игры, партнёрская программа и гостевые лендинги;
- отдельные входы Google и Discord;
- обязательная подписка сразу на несколько каналов и визуальный граф рефералов;
- общий межпроектовый чёрный список.

Уже есть свои аналоги: тарифы, лимиты трафика и устройств, пробный период, кошелёк, подарки, автопродление, промокоды включая дни, рефералы, рассылки, RBAC, бэкапы, техрежим, антифрод, кабинет email/Telegram/VK/Яндекс, CMS меню и sandbox.

## Аудит этой версии / Audit in this release

- Обзор админки, `GET /api/admin/remnawave/nodes` и `GET /api/admin/remnawave/health` больше не отдают сырой JSON узлов и текст исключения Remnawave.
- Публичное имя узла, похожее на URL или IP, заменяется на `node`.
- Проверка health summary для Remnawave больше не кладёт `str(exception)` в ответ.
- Каталог `GET /api/plans` пропускает якорные тарифы конструктора.
- Покупка, кошелёк, пробный период и подарок не принимают якорный `plan_id` без расчёта конструктора.
- `subscription_active` в пользовательском статусе учитывает срок и состояние подписки, а не просто наличие даты.

Полный прогон исходников: `python3 -m pytest -q`. Прогон без касс против поднятого API: `bash scripts/sandbox-e2e.sh`.
