import ast, pathlib, re, yaml
ROOT=pathlib.Path(__file__).resolve().parents[1]

def read(p): return p.read_text(encoding="utf-8")

def test_all_python_parse():
    for p in (ROOT/"backend").rglob("*.py"): ast.parse(read(p))

def test_v21_contracts():
    main=read(ROOT/"backend/app/main.py"); sec=read(ROOT/"backend/app/security.py"); models=read(ROOT/"backend/app/models.py"); rem=read(ROOT/"backend/app/remnawave.py")
    for x in [
        'APP_VERSION = "43.1.0-production"','/metrics','/api/admin/payments/reconcile','/api/admin/sessions/revoke-all',
        '/api/me/connection-qr','/api/me/auto-renew','auto_renew_scheduler','reconciliation_scheduler','_safe_extract_members',
        'S3 remote size verification failed','Valid MFA code is required for restore','PaymentProviderEvent','ReferralLedger','AutoRenewMethod'
    ]: assert x in main or x in models
    assert 'RemnawaveCircuitOpen' in rem and 'remnawave_cb_failures' in read(ROOT/"backend/app/config.py")
    assert 'security.stepup' in sec and 'payments.reconcile' in sec

def test_worker_is_separate():
    s=read(ROOT/"backend/worker.py"); c=yaml.safe_load(read(ROOT/"docker-compose.yml"))
    assert 'backup_scheduler' in s and 'auto_renew_scheduler' in s and 'worker' in c['services']
    assert c['services']['worker']['command']==['python','worker.py']

def test_compose_ports():
    c=yaml.safe_load(read(ROOT/"docker-compose.yml"))
    assert set(c['services']['caddy']['ports'])=={'80:80','443:443','443:443/udp'}
    for name in ['db','redis','backend','worker','bot','admin','miniapp']: assert not c['services'][name].get('ports')

def test_admin_ui_contracts():
    s=read(ROOT/"admin/src/main.tsx"); assert '/api/admin/payments/reconcile' in s; assert '/api/admin/sessions/revoke-all' in s; assert 'req("/health")' in s

def test_miniapp_contracts():
    s=read(ROOT/"miniapp/src/main.tsx"); assert '/api/me/connection-qr' in s; assert 'Автопродление' in s; assert 'Реферальная программа' in s

def test_no_unsafe_restore_extract():
    s=read(ROOT/"backend/app/main.py"); assert 'tar.extract(member,path=work)' not in s; assert '_safe_extract_members' in s

def test_migration_chain():
    versions=[]
    for p in sorted((ROOT/"backend/alembic/versions").glob("*.py")):
        s=read(p); m=re.search(r'revision\s*=\s*["\']([^"\']+)',s); d=re.search(r'down_revision\s*=\s*["\']([^"\']+)',s)
        assert m; versions.append((m.group(1),d.group(1) if d else None))
    assert any(r=='0009_v20_v21' and d=='0008_v16_v19' for r,d in versions)
