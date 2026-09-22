# Remnawave VPN Shop 2.6.0

Предыдущий релиз **2.5.0** закрыл конструктор тарифов и безопасный статус узлов Remnawave. **2.6.0** добавляет операторскую платформу по мотивам публичного описания [Case211/remnawave-admin](https://github.com/Case211/remnawave-admin): скоринг, агент узла, ключи API, подписанные webhook, исходящая почта, метрики, команда бота, темы и установка кабинета на домашний экран.

The previous release **2.5.0** added the tariff constructor and safe Remnawave node status. **2.6.0** adds an operator platform inspired by the public description of Case211/remnawave-admin: scoring, a node agent, API keys, signed webhooks, outbound mail, metrics, a bot command, themes and a cabinet home-screen install.

Исходный код remnawave-admin в этот репозиторий не копировался. Правила скоринга, агент и маршруты написаны заново.

## Что вошло

- Семь анализаторов плюс флаг торрента: temporal, geo, ASN, behavior, devices, HWID, user-agent, torrent. IPv4 схлопывается до /24, IPv6 до /64. Мобильные префиксы получают буфер CGNAT. Организации с признаком хостинга этот буфер не получают.
- Рекомендация по баллу: observe, warn, review, throttle, block. Нарушение создаётся, когда балл не ниже `min_score` (по умолчанию 50). Автоматическое ограничение аккаунта выключено, пока администратор не включит `auto_hard_block`.
- Агент `scripts/node-agent.py` шлёт heartbeat и наблюдения. API отдаёт ему только действия `throttle` и `clear`. Ограничение трафика применяется на узле только при `AGENT_APPLY_TC=1` и только для одного глобального IP.
- Чёрный список HWID: `block` отвечает 403 «Устройство в чёрном списке», `alert` пускает регистрацию и пишет открытое нарушение.
- Ограничение пользователя (`restricted_at`) запрещает пробный период, создание платежа и списание кошелька. Разбор нарушения может отключить пользователя в Remnawave.
- Ключ API `rw_…` показывается один раз, хранится как SHA-256 и открывает `GET /api/v3/status` при scope `read`.
- Исходящий webhook подписывается HMAC в заголовке `X-Shop-Signature` и уходит через DNS-pinned клиент. Секрет шифруется.
- SMTP-проверка пишет письмо только администратору, который нажал кнопку. DKIM сохраняет закрытый ключ в зашифрованном виде и показывает TXT-запись.
- Prometheus на `/metrics` добавляет `vpnshop_abuse_open`, `vpnshop_agents_online`, `vpnshop_webhook_failures`, когда модуль `metrics` включён. Дашборд: `deploy/grafana/vpnshop-platform.json`.
- Команда бота `/ops` отвечает только `ADMIN_TELEGRAM_ID`.
- Семь тем админки: dark, light, midnight, graphite, lagoon, amber, paper. Цвет по умолчанию сохранён.
- Кабинет объявляет `cabinet/public/manifest.webmanifest`, чтобы его можно было поставить на домашний экран.
- Встроенные переключатели модулей: abuse, agent, webhooks, mail, metrics, torrents.
- География в админке — число наблюдений по коду страны.

## Границы версии

- Агент не открывает интерактивный терминал и не принимает произвольные команды.
- Почта — исходящий SMTP и TXT для DKIM. Приём почты, открытый relay и проверка SPF/DMARC в этот релиз не входят.
- Признак торрента приходит флагом от агента. Разбор пакетов nDPI в процесс API не встроен.
- Внешний API v3 в этой версии — статус по ключу со scope `read`.
- Модули — шесть встроенных переключателей. Загрузка чужого кода и магазин плагинов отсутствуют.
- Отдельного Android APK в релизе нет: кабинет ставится как PWA.
- Карта мира в интерфейсе не встроена: есть счётчики стран.
- `auto_hard_block` по умолчанию выключен.

## Лицензия

Выбрана **Remnawave VPN Shop Proprietary License 1.0** (`SPDX-License-Identifier: LicenseRef-Proprietary`). Текст — в файле `LICENSE` на русском и английском. Чтение репозитория разрешено. Копирование, изменение, распространение и предоставление как услуги требуют письменного разрешения владельца репозитория. Лицензия AGPL стороннего проекта не применяется к этому коду.

The project license is the Remnawave VPN Shop Proprietary License 1.0. See `LICENSE`.

## Проверка

```bash
python3 -m compileall -q backend
python3 -m pytest -q
bash -n scripts/node-agent.py
cd admin && npx vite build
cd ../cabinet && npx vite build
```

Прогон без платёжных шлюзов остаётся прежним: `PAYMENTS_SANDBOX=true` и `bash scripts/sandbox-e2e.sh`. Он описан в `INSTRUCTION.md`, раздел 9.4.
