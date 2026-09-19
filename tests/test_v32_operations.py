from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def read(p): return p.read_text()

def test_current_manifest_and_migration():
    m=read(ROOT/'release-manifest.template.json')
    mig=read(ROOT/'backend/alembic/versions/0017_v39_staging_isolation.py')
    assert '43.1.0-production' in m
    assert '0017_v39_staging_isolation' in m
    assert 'class Job' in read(ROOT/'backend/app/models.py')
    assert 'class FraudSignal' in read(ROOT/'backend/app/models.py')
    assert 'class PayoutTransaction' in read(ROOT/'backend/app/models.py')
    assert 'revision="0017_v39_staging_isolation"' in mig

def test_current_ops_endpoints_and_rbac():
    main=read(ROOT/'backend/app/main.py'); sec=read(ROOT/'backend/app/security.py')
    for x in ['/api/admin/monitoring','/api/admin/jobs','/api/admin/fraud','/api/admin/payouts','/api/me/privacy/export','/api/me/privacy/account','/api/me/traffic','/api/admin/refunds/{refund_id}/reconcile']:
        assert x in main
    for x in ['referrals.withdrawals.read','referrals.withdrawals.approve','referrals.withdrawals.pay','referrals.reconcile']:
        assert x in sec
    assert 'Manual mark-refunded is disabled' in main

def test_build_stage_images_are_pinnable():
    compose=read(ROOT/'docker-compose.yml')
    for x in ['PYTHON_BASE_IMAGE','NODE_BASE_IMAGE','NGINX_BASE_IMAGE']:
        assert x in compose
    assert 'ARG PYTHON_BASE_IMAGE' in read(ROOT/'backend/Dockerfile')
    assert 'ARG NODE_BASE_IMAGE' in read(ROOT/'admin/Dockerfile')
    assert 'ARG NGINX_BASE_IMAGE' in read(ROOT/'admin/Dockerfile')
