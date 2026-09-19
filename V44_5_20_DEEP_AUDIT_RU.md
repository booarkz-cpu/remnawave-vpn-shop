# Remnawave VPN Shop 44.5.20 Enterprise — очень глубокий аудит

## Итог

Выполнен повторный полный аудит релиза 44.5.19 с отдельным приоритетом на ранее оставшийся DNS-rebinding / TOCTOU risk в hostname-based monitoring.

**Результат: 231/231 regression-тестов проходят.**

Новая версия: **44.5.20-enterprise**.

Migration head остаётся `0030_v44_5_16_privacy_and_refund_integrity`: для исправления DNS/HTTP transport schema migration не требуется.

## Критическое исправление: DNS rebinding / TOCTOU

### Проблема

Предыдущая реализация проверяла hostname через `socket.getaddrinfo()` во время валидации URL, а затем HTTP-клиент мог самостоятельно выполнить новое DNS-разрешение. Между этими операциями DNS-ответ мог измениться, поэтому проверенный public IP не гарантировал, что фактическое TCP-соединение будет установлено к тому же адресу.

Это классический DNS rebinding / TOCTOU SSRF risk. OWASP прямо указывает, что DNS-проверка перед запросом недостаточна, если клиент выполняет отдельное разрешение во время использования URL, и рекомендует учитывать DNS rebinding/TOCTOU, отключать redirects и контролировать фактический destination. См. OWASP SSRF Prevention Cheat Sheet.

### Исправление

Добавлен `_PinnedPublicDNSBackend` поверх httpcore:

1. перед каждым новым TCP connection hostname разрешается непосредственно transport layer;
2. проверяются **все** полученные A/AAAA адреса;
3. любой private/local/reserved/link-local/multicast/unspecified/non-global ответ приводит к отказу;
4. выбранный public IP передаётся нижележащему TCP connector как **literal IP**;
5. HTTP origin hostname при этом сохраняется для TLS SNI/certificate verification;
6. следующий DNS lookup для самого TCP connection больше не выполняется;
7. HTTP redirects отключены;
8. `trust_env=False`, поэтому `HTTP_PROXY`/`HTTPS_PROXY` из окружения не может перенаправить monitoring request через неожиданный proxy;
9. создание monitoring target и runtime request используют одну и ту же public-IP policy.

Таким образом, между DNS validation и TCP connect больше нет второй hostname-based DNS resolution, которая позволяла бы rebinding-атаку.

## Дополнительные проверки

Повторно проверены:

- payment intent/idempotency;
- provider webhook binding;
- late webhook после refund;
- refund/fulfillment concurrency;
- auto-renew/refund concurrency;
- withdrawal/payout state machine;
- account deletion/provisioning race;
- JWT invalidation после deletion;
- referral ledger;
- promo reservation;
- Remnawave entitlement/revoke/recovery;
- uploads и bounded reads;
- branding assets;
- admin RBAC/CSRF boundaries;
- backup/restore/test-restore;
- Alembic migration chain;
- release tooling;
- dependency pinning;
- frontend theme/branding implementation.

## Branding/UI

Сохранены возможности 44.5.19:

- light/dark theme;
- custom panel name;
- custom logo;
- custom favicon;
- branding на login/sidebar;
- серверная валидация и нормализация image assets;
- безопасные generated filenames;
- ограничения размера upload.

## Verification

- `pytest -q` → **231 passed**
- `python -m compileall -q backend` → PASS
- `bash -n install.sh deploy/*.sh scripts/*.sh` → PASS
- Docker Compose YAML parse → PASS
- DNS pinning focused tests → **3 passed**
- ZIP integrity → PASS
- SHA-256 → PASS
- release version consistency → PASS
- migration head consistency → PASS

## Ограничения

Production YooKassa/Platega/RollyPay E2E и live Remnawave API не доступны в этой среде, поэтому они не выдаются за фактически выполненные production tests.

Полный browser/Vite production build требует установленного `admin/node_modules`; в исходном архиве зависимости frontend не поставляются и `node_modules` исключается из release ZIP.

## Security verdict

Ранее документированный DNS-rebinding / TOCTOU risk для hostname-based monitoring **устранён на application transport layer**: фактический TCP connect выполняется к IP, проверенному непосредственно перед соединением, без повторного DNS lookup.

Дополнительная defense-in-depth мера всё равно рекомендуется на инфраструктурном уровне: firewall/network policy должна разрешать API только необходимые исходящие направления.
