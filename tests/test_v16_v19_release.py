import ast, pathlib, re, yaml
ROOT=pathlib.Path(__file__).resolve().parents[1]
MAIN=ROOT/'backend/app/main.py'
SEC=ROOT/'backend/app/security.py'
MODELS=ROOT/'backend/app/models.py'
COMPOSE=ROOT/'docker-compose.yml'

def read(p): return p.read_text(encoding='utf-8')

def test_python_compiles():
    for p in (ROOT/'backend/app').glob('*.py'):
        ast.parse(read(p))

def test_main_has_v19_features():
    s=read(MAIN)
    for x in ['APP_VERSION = "43.1.0-production"','/api/admin/analytics','/api/admin/sessions','/api/admin/payments/{payment_id}/retry','/api/admin/backups/{backup_id}/verify','/api/admin/backups/{backup_id}/restore','/api/me/referral','/api/me/subscription','fulfillment_retry_scheduler','expiry_notification_scheduler']:
        assert x in s
    m=re.search(r'async def admin_menu_delete.*?(?=\n@app|\Z)',s,re.S); assert m and 'payload' not in m.group(0)

def test_security_session_and_permissions():
    s=read(SEC)
    assert 'AdminSession' in s and 'claims.get("jti")' in s
    assert 'users.keys' in s and 'sessions.manage' in s and 'backups.write' in s

def test_models():
    s=read(MODELS)
    for x in ['AdminSession','PromoRedemption','ReferralReward','fulfillment_status','next_retry_at','idempotency_key','referral_code','referral_balance']:
        assert x in s

def test_migration_chain():
    files=sorted((ROOT/'backend/alembic/versions').glob('*.py'))
    revisions=[]; downs=[]
    for p in files:
        s=read(p); m=re.search(r'revision\s*=\s*["\']([^"\']+)',s); d=re.search(r'down_revision\s*=\s*["\']([^"\']+)',s)
        assert m, p; revisions.append(m.group(1)); downs.append(d.group(1) if d else None)
    assert len(revisions)==len(set(revisions))
    assert '0008_v16_v19' in revisions and '0007_v15_production' in downs

def test_compose_private_ports():
    c=yaml.safe_load(read(COMPOSE))
    assert set(c['services']['caddy']['ports'])=={'80:80','443:443','443:443/udp'}
    for name in ['db','redis','backend','bot','admin','miniapp']:
        assert not c['services'][name].get('ports')

def test_no_float_money_in_discount_logic():
    s=read(MAIN)
    assert 'price * value / Decimal("100")' in s

def test_env_s3():
    s=read(ROOT/'.env.example')
    for x in ['S3_ENDPOINT_URL','S3_BUCKET','S3_ACCESS_KEY','S3_SECRET_KEY','REFERRAL_REWARD_PERCENT']:
        assert x in s
