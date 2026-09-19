# Remnawave VPN Shop 44.5.5 Enterprise — глубокий аудит и исправления

Дата: 2026-09-14

## Найдено и исправлено

### HIGH — повторная покупка после refund не восстанавливала доступ
Refund безопасно отключает remote user. При следующей оплаченной покупке существующий Remnawave user раньше только продлевался, но не включался обратно. Исправлено: fulfillment проверяет remote status и вызывает `enable_user` для `disabled/blocked/inactive`.

### HIGH — конкурентное создание refund request могло давать 500
Два администратора могли одновременно увидеть отсутствие `RefundRequest` и создать две записи, после чего уникальный constraint приводил к `IntegrityError`. Исправлено row-level lock на Payment и RefundRequest.

### MEDIUM — trial мог оставить отключённого Remnawave user отключённым
Аналогичная проблема была в worker-пути выдачи trial. Исправлено восстановление remote access перед продлением существующего пользователя.

### MEDIUM — auto-renew не фиксировал коммерческие условия покупки
Auto-renew создавал Payment без snapshot duration/traffic/device/profile. Если тариф изменяли между созданием платежа и fulfillment, уже списанная сумма могла получить новые условия тарифа. Исправлено: auto-renew сохраняет immutable entitlement snapshot так же, как обычный checkout.

### MEDIUM — public config рекламировал отключённые/circuit-open providers
`/api/public/config` показывал провайдера только по наличию credentials и мог расходиться с фактическим routing. Исправлено: публичный список провайдеров использует тот же routing/health gate, что и checkout.

## Регрессии

Добавлен `tests/test_v45_5_deep_regressions.py`.

## Проверки

- `pytest -q` — **144 passed**
- `python -m compileall -q backend` — PASS
- `bash -n install.sh deploy/*.sh scripts/*.sh` — PASS
- source AST parsing — PASS
- release version consistency — PASS

## Ограничения

Реальные production credentials платёжных систем, живой Remnawave API и Docker daemon недоступны в sandbox. Production E2E, реальный PostgreSQL restore и runtime container tests не объявляются пройденными без соответствующей среды.

Методология аудита ориентирована на business logic, state transitions, concurrency, authorization, payment integrity и security boundaries; это соответствует рекомендациям OWASP по manual secure code review и ASVS. 
