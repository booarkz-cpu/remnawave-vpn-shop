# Release Notes — 2.0.4-audited

## Security
- Закрыт SSRF/DNS-rebinding в staging E2E.
- Все staging external URLs ограничены абсолютным HTTPS и глобально маршрутизируемыми адресами.
- Staging provider requests используют DNS pinning.
- Redirect following отключён для staging runner.

## Release tooling
- Runtime/build/installer/manifest синхронизированы на `2.0.4-audited`.
- Regression identity tests обновлены для текущего релиза.

## Verification
`276 passed`.

## Database
Migration head не изменён: `0032_v2_0_0_product_features`.
Отдельная migration для 2.0.4 не требуется.

## Known verification limits
Live provider/Telegram/Remnawave E2E, Docker vulnerability scan, npm audit и SBOM требуют внешних сервисов/инструментов и не выполнялись в текущей среде.
