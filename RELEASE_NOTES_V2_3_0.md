# Remnawave VPN Shop 2.3.0

## Русский

- Установщик `install.sh` больше не публикует порты API и панелей. Он запускает `deploy/install-vps.sh`, где вводятся все операторские настройки. `INSTALL_NONINTERACTIVE=1` позволяет передать их переменными окружения.
- Внутренний кошелёк: пополнение через YooKassa, Platega или RollyPay и оплата тарифа с баланса.
- Покупка подарка с баланса, deep-link `t.me/<bot>?start=GIFT_...` и запрет активировать собственный подарок.
- Промокод вида `days` добавляет дни и не списывает эту величину как скидку в валюте.
- Необязательная проверка подписки на Telegram-канал перед оплатой.
- Автопродление начинается за `AUTO_RENEW_LEAD_DAYS` дней (по умолчанию 3).
- Миграция `0035_v2_3_0_wallet_gifts`.

Идеи кошелька, подарков и обязательного канала сверены с публичным описанием Bedolaga (MIT) и написаны заново под эту схему данных. Исходный код того репозитория не копировался.

## English

- `install.sh` no longer publishes the API or panel ports. It execs `deploy/install-vps.sh`, which collects every operator setting. `INSTALL_NONINTERACTIVE=1` reads those settings from the environment.
- Internal wallet: top up through YooKassa, Platega or RollyPay, then pay for a plan from the balance.
- Gift purchase from the balance, a `t.me/<bot>?start=GIFT_...` deep link, and a ban on redeeming your own gift.
- A `days` promo adds days and is not applied as a currency discount.
- Optional required Telegram channel membership before checkout.
- Auto-renew starts `AUTO_RENEW_LEAD_DAYS` days before expiry (default 3).
- Migration `0035_v2_3_0_wallet_gifts`.

The wallet, gift and required-channel ideas follow the public Bedolaga description (MIT) and were written for this schema. That repository's source was not copied.
