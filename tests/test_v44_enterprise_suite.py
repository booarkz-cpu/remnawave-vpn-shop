from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/"backend/app/main.py").read_text(); MODELS=(ROOT/"backend/app/models.py").read_text(); MIG=(ROOT/"backend/alembic/versions/0022_enterprise_suite.py").read_text(); ADMIN=(ROOT/"admin/src/main.tsx").read_text(); WORKER=(ROOT/"backend/worker.py").read_text()

def test_v44_contract_and_migration_chain():
    assert 'APP_VERSION = "44.5.5-enterprise"' in MAIN
    assert '0022_enterprise_suite' in MIG and '0021_v43_hardening_docs' in MIG
    for name in ['UserDevice','Campaign','AutomationRule','MonitoringCheck','TrialGrant']:
        assert f'class {name}' in MODELS
    for route in ['/api/me/devices','/api/me/trial','/api/admin/enterprise/monitoring','/api/admin/enterprise/campaigns','/api/admin/enterprise/rules','/api/admin/enterprise/summary']:
        assert route in MAIN
    assert 'job.kind=="trial"' in WORKER

def test_v44_admin_surface():
    assert 'Корпоративный контур' in ADMIN
    for label in ['24/7 мониторинг','Campaign Manager','Rules Engine','мультиустройства','Trial']:
        assert label in ADMIN

def test_monitoring_is_https_only_and_no_arbitrary_rule_code():
    assert 'validate_public_url(payload.url)' in MAIN
    assert 'actions' in MAIN and 'subprocess' not in MAIN[MAIN.find('@app.post("/api/admin/enterprise/rules")'):MAIN.find('@app.get("/api/admin/enterprise/summary")')]

def test_v44_security_and_device_limit_hardening():
    assert 'socket.getaddrinfo' in MAIN
    assert 'is_private' in MAIN and 'Monitoring hostname resolves to a private' in MAIN
    assert 'Достигнут лимит устройств тарифа' in MAIN
    assert 'active_count' in MAIN and 'UserDevice.status=="active"' in MAIN
    assert 'remote_expiry=await rw.get_expiry(remote_id)' in WORKER


def test_v44_5_release_tooling_is_consistent():
    build=(ROOT/"scripts/build-release.sh").read_text()
    installer=(ROOT/"deploy/install-vps.sh").read_text()
    manifest=(ROOT/"release-manifest.template.json").read_text()
    assert 'VERSION="1.0.0-realise"' in build
    assert 'remnawave_vpn_shop_v1_0_0_realise_deep_audited_fixed.zip' in build
    assert 'INSTALLER_VERSION="1.0.0-realise"' in installer
    assert 'V44.5 Enterprise' in installer
    assert 'previous_migration_head": "0021_v43_hardening_docs"' in manifest
    assert 'remnawave_vpn_shop_v1_0_0_realise_deep_audited_fixed_manifest.json' in manifest


def test_payment_provider_health_bootstraps_without_admin_page():
    src=MAIN
    assert 'bootstrap the provider-health records lazily' in src
    assert 'PaymentProviderHealth(provider=p,priority=i*10,enabled=True)' in src

def test_auto_renew_respects_production_gate_and_payments_flag():
    src=MAIN
    marker='async def auto_renew_scheduler()'
    block=src[src.index(marker):src.index('async def reconciliation_scheduler()')]
    assert 'PRODUCTION_PAYMENTS_GATE_KEY' in block
    assert 'feature_enabled(db, "payments", True)' in block
