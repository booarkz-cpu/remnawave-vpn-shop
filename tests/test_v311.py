"""3.1.1 staging gate instructions and secret-preservation contracts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_version_311_is_first():
    main = (ROOT / "backend/app/main.py").read_text()
    assert main.index('APP_VERSION = "3.1.1"') < main.index('APP_VERSION = "3.1.0"')
    assert main.index('APP_VERSION = "3.1.0"') < main.index('APP_VERSION = "3.0.1"')
    assert main.index('APP_VERSION = "3.0.1"') < main.index('APP_VERSION = "3.0.0-realise"')
    build = (ROOT / "scripts/build-release.sh").read_text()
    assert build.index('VERSION="3.1.1"') < build.index('VERSION="3.1.0"')
    assert "remnawave_vpn_shop_v3_1_1_full_release.zip" in build
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    assert installer.index('INSTALLER_VERSION="3.1.1"') < installer.index('INSTALLER_VERSION="3.1.0"')


def test_blank_staging_secrets_are_preserved_and_output_is_redacted():
    main = (ROOT / "backend/app/main.py").read_text()
    block = main[main.index("async def update_staging_e2e_config"): main.index("def _redact_staging_output")]
    assert "previous=await _staging_config(db) or {}" in block
    assert 'for key in ("remnawave_token","user_bearer_token","yookassa_shop_id","yookassa_secret_key","platega_merchant_id","platega_secret","rollypay_api_key","rollypay_signing_secret")' in block
    assert "Укажите токен Remnawave для staging" in block
    assert "production-платёжные credentials" in block
    redact = main[main.index("def _redact_staging_output"): main.index("async def _run_staging_e2e")]
    assert "[скрыто]" in redact
    assert "yookassa_secret_key" in redact
    assert "yookassa_shop_id" not in redact
    assert "platega_merchant_id" not in redact
    assert '"FULL_E2E_PASS" in text' in main
    assert 'status.get("full_e2e")' in main


def test_runner_prints_checkout_and_image_has_curl():
    host = (ROOT / "scripts/staging-e2e.sh").read_text()
    image = (ROOT / "backend/scripts/staging-e2e.sh").read_text()
    assert host == image
    for text in (host, image):
        assert "[CHECKOUT]" in text
        assert "FULL_E2E_PASS" in text
        assert "startswith('https://')" in text
        assert "awaiting_checkout" in text
        assert "в контейнере backend нет curl" in text
    docker = (ROOT / "backend/Dockerfile").read_text()
    assert "curl" in docker
    assert "COPY scripts/staging-e2e.sh ./staging-e2e.sh" in docker


def test_admin_requires_sandbox_confirmation():
    ui = (ROOT / "admin/src/main.tsx").read_text()
    i18n = (ROOT / "admin/src/i18n.tsx").read_text()
    assert "Подтверждаю sandbox-ключи" in ui
    assert "staging_confirmed:!!cfg.staging_confirmed" in ui
    assert "staging_confirmed:true" not in ui
    assert "client-logo" not in ui
    assert "Подтвердите, что это sandbox-ключи" in ui
    assert i18n.count('"Подтверждаю sandbox-ключи"') == 1
    assert "I confirm these are sandbox keys" in i18n


def test_docs_explain_gate_and_install_in_both_languages():
    steps = (ROOT / "INSTALL_STEPS.md").read_text()
    instruction = (ROOT / "INSTRUCTION.md").read_text()
    readme = (ROOT / "README.md").read_text()
    security = (ROOT / "SECURITY.md").read_text()
    notes = (ROOT / "RELEASE_NOTES_V3_1_1.md").read_text()
    docs = (ROOT / "DOCUMENTATION.md").read_text()
    assert "## Русский" in steps and "## English" in steps
    assert "sudo bash install.sh" in steps
    assert "INSTALL_NONINTERACTIVE" in steps
    assert "BASE_DOMAIN" in steps and "CABINET_DOMAIN" in steps
    assert "Разрешить реальные платежи" in steps
    assert "Allow live payments" in steps
    assert instruction.count("## 9.15.") == 2
    assert "FULL_E2E_PASS" in instruction
    assert "Разрешить реальные платежи" in instruction
    assert "Allow live payments" in instruction
    assert "Сначала необходимо успешно завершить полный staging E2E" in instruction
    assert "Результат staging E2E устарел" in instruction
    assert "3.1.1" in readme and "3.1.0" in readme and "3.0.1" in readme
    assert "INSTALL_STEPS.md" in readme and "9.15" in readme
    assert "личный кабинет" in readme and "Конструктор тарифов" in readme
    assert "3.1.1" in security and "[скрыто]" in security and "FULL_E2E_PASS" in security
    assert "3.1.0" in security
    assert "3.1.1" in notes and "Русский" in notes and "English" in notes
    assert "2.10.0" in notes and "2.12.0" in notes and "0038_v2_6_0_platform" in notes
    assert "INSTALL_STEPS.md" in docs and "RELEASE_NOTES_V3_1_1.md" in docs
