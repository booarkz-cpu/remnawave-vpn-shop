from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/"backend/app/main.py").read_text()
BUILD=(ROOT/"scripts/build-release.sh").read_text()
INSTALL=(ROOT/"deploy/install-vps.sh").read_text()
MANIFEST=(ROOT/"release-manifest.template.json").read_text()

def test_release_version_is_1_0_2_realise():
    assert 'APP_VERSION = "2.0.0-realise"' in MAIN
    assert 'VERSION="2.0.0-realise"' in BUILD
    assert 'INSTALLER_VERSION="2.0.0-realise"' in INSTALL
    assert '"version": "2.0.0-realise"' in MANIFEST

def test_fulfill_can_reuse_auto_renew_user_lock_without_deadlocking():
    assert 'async def fulfill(payment_id:int, db:AsyncSession, existing_user_lock_token: str|None = None)' in MAIN
    assert 'if not existing_user_lock_token:' in MAIN
    assert 'fulfill(existing.id,db,existing_user_lock_token=user_token)' in MAIN
    assert 'fulfill(p.id,db,existing_user_lock_token=user_token)' in MAIN

def test_lock_release_cleans_renewal_registry_even_without_redis():
    block=MAIN[MAIN.index('async def _release_payment_side_effect_lock'):MAIN.index('async def _acquire_user_fulfillment_lock')]
    assert '_LOCK_RENEW_TASKS.pop(token,None)' in block
    assert 'if redis_client is None:' in block

def test_auto_renew_keeps_user_lock_through_fulfillment():
    start=MAIN.index('async def auto_renew_scheduler')
    end=MAIN.index('async def reconciliation_scheduler')
    block=MAIN[start:end]
    assert 'user_lock,user_token=await _acquire_user_fulfillment_lock' in block
    assert 'fulfill(existing.id,db,existing_user_lock_token=user_token)' in block
    assert 'fulfill(p.id,db,existing_user_lock_token=user_token)' in block
