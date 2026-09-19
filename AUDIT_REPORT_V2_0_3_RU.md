# Критический аудит Remnawave VPN Shop 2.0.3-audited

## Статус

Повторный аудит релиза 2.0.2-audited выполнен после распаковки итогового ZIP и независимого запуска тестового набора.

## Найденная критическая ошибка

**C-06 — рассинхронизация версии production installer.** `backend/app/main.py`, release manifest и build script указывали 2.0.2-audited, однако `deploy/install-vps.sh` продолжал записывать `APP_VERSION=2.0.0-realise`. При установке через штатный production installer фактическая версия окружения могла не соответствовать выпущенному артефакту, что ломает release identity, диагностику и контроль версии.

### Исправление

- `deploy/install-vps.sh`: `INSTALLER_VERSION=2.0.3-audited`.
- Баннер installer синхронизирован с 2.0.3-audited.
- `INSTALL.md` синхронизирован.
- Добавлен `tests/test_v2_0_3_release_identity.py`, проверяющий runtime/build/installer/manifest/documentation consistency.

## Проверки

- полный pytest: PASS
- Python compileall: PASS
- shell syntax: PASS
- Docker Compose YAML parse: PASS
- ZIP integrity: PASS
- detached SHA-256 manifest: PASS

Live E2E с реальными внешними credentials и deployment в production в этой среде не выполнялся.
