from pathlib import Path
import yaml
ROOT=Path(__file__).parents[1]

def test_v33_version_and_env_example():
    assert 'APP_VERSION = "43.1.0-production"' in (ROOT/'backend/app/main.py').read_text()
    env=(ROOT/'.env.example').read_text()
    assert 'APP_SECRET_PREVIOUS=' in env
    assert 'BACKUP_S3_ENABLED=false' in env
    assert 'REFERRAL_REWARD_PERCENT=' in env

def test_compose_restart_policy_is_service_level():
    d=yaml.safe_load((ROOT/'docker-compose.yml').read_text())
    for name in ('admin','miniapp'):
        assert d['services'][name]['restart']=='unless-stopped'
        assert 'restart' not in d['services'][name]['build']['args']

def test_durable_job_worker_and_recovery():
    w=(ROOT/'backend/worker.py').read_text()
    assert 'async def job_worker()' in w
    assert 'skip_locked=True' in w
    assert 'timedelta(minutes=10)' in w
    assert 'main.fulfill(payment_id,db)' in w

def test_fulfillment_updates_job_on_failure():
    m=(ROOT/'backend/app/main.py').read_text()
    assert 'job.status="failed" if terminal else "queued"' in m
    assert 'job.worker_id=None' in m

def test_refund_reconcile_calls_provider_adapter():
    m=(ROOT/'backend/app/main.py').read_text()
    assert 'provider.get_refund_status(r.provider_refund_id)' in m
    assert 'Provider refund status: {status}' in m

def test_provider_interface_is_complete():
    p=(ROOT/'backend/app/payments.py').read_text()
    for x in ('async def create','async def refund','async def get_refund_status','async def verify_succeeded'):
        assert x in p

def test_v33_release_builder_exists():
    p=ROOT/'scripts/build-release.sh'
    assert p.exists() and p.stat().st_mode & 0o111
    assert 'sha256sum' in p.read_text()
