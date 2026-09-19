# V44.4 — максимальный аудит и исправления

Дата: 2026-09-14

## Найденные и исправленные проблемы

### 1. Повторное использование Idempotency-Key с другим заказом
Ранее существующий платёж возвращался только по паре `user_id + Idempotency-Key`. Это позволяло случайно повторно использовать тот же ключ для другого тарифа/промокода и получить старый платёж.

Исправлено: при найденном платеже дополнительно проверяются `plan_id`, `promo_code` и итоговая сумма; при несовпадении возвращается HTTP 409.

### 2. Возможный откат локального срока подписки
После успешного remote extension локальная запись могла сохранять рассчитанный `expected_after`, хотя Remnawave уже вернул более поздний срок из-за параллельной операции.

Исправлено в обычном fulfillment и Trial Worker: используется подтверждённый удалённый `expires_at`, причём локальный срок никогда не уменьшается.

## Автоматические проверки

- `pytest`: 116 passed
- Python `compileall`: OK
- Bash `-n` для всех scripts/deploy scripts: OK
- Docker Compose YAML parse: OK
- migration chain: OK
- ZIP integrity: OK
- release version consistency: OK
- payment idempotency regression: OK
- remote expiry monotonicity regression: OK

## Ограничения среды

Docker daemon и реальные внешние sandbox credentials платёжных провайдеров недоступны. Поэтому реальный container runtime и внешний provider E2E не объявляются пройденными. Production payment gate должен оставаться fail-closed до выполнения staging E2E в целевой инфраструктуре.
