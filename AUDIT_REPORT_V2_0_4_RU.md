# Критический аудит Remnawave VPN Shop 2.0.4-audited

## Область
Проверены backend API, authentication/session lifecycle, платежи и fulfillment, Remnawave integration, worker/schedulers, bot, provisioning, backup/restore tooling, staging E2E, Docker/Compose, deployment scripts, frontend source, release identity и regression suite.

## Найденный критический дефект
### C-07 — SSRF/DNS-rebinding через staging E2E endpoints
Администратор мог сохранить произвольные HTTPS URL для staging public/Remnawave/payment endpoints. Позже сервер и shell runner обращались к этим URL без полной проверки глобальной маршрутизации; `curl` также мог следовать редиректам. Это создавало путь к обращениям из production-сети к внутренним адресам и потенциальной передаче staging credentials.

### Исправление
- staging `public_base_url`, `remnawave_url` и все provider API URLs проходят `validate_public_url()`;
- запрещены localhost/private/non-global destinations;
- staging payment HTTP requests используют pinned public DNS transport;
- provider endpoints дополнительно валидируются непосредственно перед запросом;
- staging runner не следует редиректам и разрешает только HTTPS для внешних целей;
- добавлены regression tests.

## Дополнительное исправление
Старый regression test `test_v2_0_3_release_identity.py` содержал жёстко зафиксированную текущую версию 2.0.3 и поэтому ломался при легитимном выпуске следующего audited-релиза. Контракт переведён на 2.0.4; исторические версии сохранены как legacy markers там, где это требуется.

## Верификация
- `pytest -q`: **276 passed**
- `python -m compileall -q backend`: PASS
- `bash -n install.sh deploy/*.sh scripts/*.sh`: PASS
- Compose YAML parse: PASS
- ZIP integrity: PASS

## Ограничения среды
Не выполнялись live production/sandbox E2E с реальными credentials, Docker image vulnerability scan, npm audit и SBOM, поскольку необходимые внешние сервисы/инструменты отсутствуют в среде. Это не маркируется как PASS.

## Итог
Критический SSRF/DNS-rebinding дефект устранён, regression coverage добавлено. Релиз 2.0.4-audited считается готовым по доступным автоматическим проверкам с указанными внешними ограничениями.
