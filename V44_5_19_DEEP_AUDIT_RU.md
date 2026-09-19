# Remnawave VPN Shop 44.5.19 Enterprise — очень глубокий аудит и UI/UX переработка

## 1. Объём проверки

Проведён повторный полный baseline-аудит V44.5.18 по backend/API, PostgreSQL/Alembic, payment state machines, webhooks, refunds/reconciliation, auto-renew, referral/withdrawal ledger, fulfillment/provisioning, Remnawave integration, authentication/MFA/CSRF/RBAC, privacy deletion, uploads, monitoring/SSRF-sensitive code, backup/restore, Docker/Compose, release tooling, зависимости и весь admin frontend.

Отдельно проведён adversarial review бизнес-инвариантов: повтор, переупорядочивание, конкурентное выполнение и обход UI напрямую через API. OWASP рекомендует явно проверять state machines, race conditions, transaction integrity, authorization, idempotency и resource limits.

## 2. Найденные и исправленные дефекты

### IMPORTANT — отсутствовал единый механизм брендирования веб-панели

Панель имела жёстко зашитые название/логотип и только тёмную тему. Это было функциональным дефектом и мешало безопасно отделять разные инсталляции/окружения.

### Исправление

Добавлен управляемый branding layer:

- собственное название панели;
- собственный логотип;
- собственный favicon;
- тема по умолчанию light/dark;
- мгновенное переключение light/dark в интерфейсе;
- сохранение пользовательского выбора темы в localStorage;
- динамический `<title>` и favicon;
- branding применяется и на странице входа, до авторизации;
- публичный endpoint `/api/public/branding` возвращает только не-секретные branding значения.

### HIGH — upload branding assets доверял raw image bytes

Для нового branding функционала нельзя было просто принимать произвольные bytes: даже корректный MIME/signature не гарантирует безопасное содержимое и metadata. OWASP рекомендует allowlist, size limits, content validation, безопасное имя и нормализацию изображений.

### Исправление

Branding uploads теперь:

- доступны только `manage_content`;
- принимают только PNG/JPEG/WEBP;
- имеют bounded read;
- ограничены 2 MiB для logo и 512 KiB для favicon;
- проверяются Pillow;
- EXIF orientation нормализуется;
- изображение декодируется и повторно кодируется в PNG;
- storage filename генерируется сервером;
- старый asset удаляется только по безопасному basename;
- SVG/HTML/активный content не принимается.

Это соответствует OWASP File Upload guidance: allowlist, content/signature validation, size limits, generated filenames и безопасное хранение.

### MEDIUM — название панели не имело собственного бизнес-лимита

Общий `SettingIn` разрешал до 100000 символов. Для UI branding это чрезмерный лимит и позволял записывать ненужные объёмы текста в title/setting.

Исправлено: `app_name` — от 1 до 255 символов после trim.

## 3. Повторно проверенные критические инварианты

Новых critical payment/security bypass в этом цикле не найдено. Повторно проверены ранее исправленные critical paths:

- durable payment intent до external charge;
- idempotency и duplicate checkout;
- provider/event deduplication;
- immutable order binding;
- поздние webhook после refund не воскресают entitlement;
- refund/fulfillment/reconciliation используют общий payment side-effect lock;
- auto-renew сериализован с refund;
- user deletion сериализован с provisioning;
- deleted users блокируются JWT lookup;
- active subscription блокирует trial;
- referral balance и withdrawal защищены conditional updates/state checks;
- approved/processing payout нельзя отклонить старым reject workflow;
- remote entitlement/quota/profile не расходятся;
- retry provisioning использует persisted expectations;
- uploads имеют bounded reads;
- admin endpoints имеют session/RBAC/CSRF controls;
- backup restore и archive extraction проверяют пути;
- staging payment endpoint доступен только localhost + runner token;
- Alembic chain имеет один head.

## 4. UI/UX переработка

Admin panel получила единый визуальный слой:

- тёмная тема сохранена как default;
- добавлена светлая тема;
- CSS variables используются для поверхностей, текста, границ, accent и status colors;
- theme toggle находится в верхней панели;
- branding отображается в sidebar и login screen;
- logo/favicons автоматически подставляются после изменения;
- responsive layout сохранён для мобильных размеров;
- отдельная страница «Брендинг панели» содержит настройки названия, темы, logo и favicon.

## 5. Security review frontend

- branding name выводится React text nodes, а не через `dangerouslySetInnerHTML`;
- asset URLs формируются сервером и хранятся как `/media/<generated-name>`;
- пользовательский filename не используется как путь storage;
- upload endpoint требует CSRF + authenticated admin session + `manage_content`;
- публичный branding endpoint не раскрывает AppSetting secrets.

## 6. Проверки

- Pytest: **227 passed**
- Python AST/compile: **OK**
- TSX transpile syntax check: **OK**
- Shell syntax: **OK**
- Docker Compose YAML parse: **OK**
- Alembic: **30 revisions**
- Alembic single head: `0030_v44_5_16_privacy_and_refund_integrity`
- ZIP integrity: проверяется release build
- SHA-256: генерируется после финального ZIP

Полный Vite production build не запускался в audit runtime, потому что `admin/node_modules` отсутствует, а `npm install` не завершился в доступное окно среды. Поэтому это не заявляется как успешный browser/runtime build. TSX source дополнительно прогнан через установленный TypeScript transpiler для проверки синтаксиса.

Production E2E с реальными YooKassa/Platega/RollyPay и live Remnawave API не выполнялся без production/staging credentials.

## 7. Residual risk

Hostname-based monitoring всё ещё имеет DNS TOCTOU risk между validation и последующим HTTP connect. Текущая защита отклоняет localhost/private/link-local/reserved targets и запрещает redirects, но полноценное устранение требует DNS pinning/custom transport.

## 8. Релиз

Версия: **44.5.19-enterprise**

Migration head: `0030_v44_5_16_privacy_and_refund_integrity`

Tests: **227**

Финальные artifact SHA-256 и detached manifest генерируются `scripts/build-release.sh` после сборки ZIP.
