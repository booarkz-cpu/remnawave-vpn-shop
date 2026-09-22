from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v250_constructor_checkout_and_monitoring_are_wired():
    main = (ROOT / "backend/app/main.py").read_text()
    tariff = (ROOT / "backend/app/tariff_api.py").read_text()
    models = (ROOT / "backend/app/models.py").read_text()
    migration = (ROOT / "backend/alembic/versions/0037_v2_5_0_tariff_constructor.py").read_text()
    cabinet_api = (ROOT / "backend/app/cabinet_api.py").read_text()
    assert 'APP_VERSION = "2.5.0"' in main
    assert "from .tariff_api import router as tariff_router" in main
    assert "app.include_router(tariff_router)" in main
    assert "quote_constructor" in main
    assert "Этот тариф собирается в конструкторе" in main
    assert "duration_days_snapshot=snap_days" in main
    assert "class TariffConstructor" in models
    assert "class TariffConstructorOption" in models
    assert 'revision = "0037_v2_5_0_tariff_constructor"' in migration
    assert 'down_revision = "0036_v2_4_0_cabinet"' in migration
    assert '@router.get("/api/tariff-constructors")' in tariff
    assert '@router.get("/api/public/servers")' in tariff
    assert '@router.get("/api/me/servers")' in tariff
    assert '@router.get("/api/admin/remnawave/monitoring")' in tariff
    assert "def public_node" in tariff
    assert '"address"' not in tariff.split("def public_node", 1)[1].split("return safe", 1)[0]
    assert "servers|custom" in cabinet_api
    assert '"/api/public/servers": 30' in main


def test_v250_frontends_expose_builder_and_servers():
    admin = (ROOT / "admin/src/main.tsx").read_text()
    cabinet = (ROOT / "cabinet/src/main.tsx").read_text()
    mini = (ROOT / "miniapp/src/main.tsx").read_text()
    assert "Конструктор тарифов" in admin
    assert "Мониторинг Remnawave" in admin
    assert "TariffConstructorPanel" in admin
    assert "RemnawaveNodes" in admin
    assert "/api/admin/tariff-constructors" in admin
    assert "/api/admin/remnawave/monitoring" in admin
    assert "constructor_id" in cabinet
    assert "/api/public/servers" in cabinet
    assert "/api/me/servers" in cabinet
    assert 'kind: "servers"' in cabinet
    assert "Конструктор тарифов" in mini
    assert "/api/tariff-constructors" in mini


def test_v250_docs_are_bilingual_and_cover_sandbox():
    readme = (ROOT / "README.md").read_text()
    instruction = (ROOT / "INSTRUCTION.md").read_text()
    security = (ROOT / "SECURITY.md").read_text()
    modules = (ROOT / "MODULES.md").read_text()
    notes = (ROOT / "RELEASE_NOTES_V2_5_0.md").read_text()
    script = (ROOT / "scripts/sandbox-e2e.sh").read_text()
    assert "2.5.0" in readme
    assert "2.4.0" in readme
    assert "Конструктор тарифов" in readme
    assert "Plan builder" in readme or "tariff constructor" in readme.lower()
    assert "PAYMENTS_SANDBOX" in instruction
    assert "scripts/sandbox-e2e.sh" in instruction
    assert "9.3" in instruction
    assert "## English" in security or "# Security" in security
    assert "Конструктор" in security
    assert "не отдаёт адреса" in security or "does not return addresses" in security
    for name in ("main.py", "cabinet_api.py", "tariff_api.py", "payments.py", "remnawave.py", "worker.py"):
        assert name in modules
    assert "English" in modules
    assert "Bedolaga" in notes
    assert "/api/public/servers" in script
    assert "/api/tariff-constructors" in script
