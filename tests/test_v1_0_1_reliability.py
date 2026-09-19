from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "backend/app/main.py").read_text()
BUILD = (ROOT / "scripts/build-release.sh").read_text()
INSTALL = (ROOT / "deploy/install-vps.sh").read_text()
MANIFEST = (ROOT / "release-manifest.template.json").read_text()


def test_release_is_v1_0_2_realise():
    assert 'APP_VERSION = "2.0.0-realise"' in MAIN
    assert 'VERSION="2.0.0-realise"' in BUILD
    assert 'INSTALLER_VERSION="2.0.0-realise"' in INSTALL
    assert '"version": "2.0.0-realise"' in MANIFEST


def test_all_renewed_distributed_locks_are_released_through_cleanup_helper():
    # Direct DEL calls bypass _LOCK_RENEW_TASKS cleanup and leak renewal tasks.
    # Only the helper is allowed to release a renewed distributed lock.
    assert 'finally:\n            await _release_payment_side_effect_lock(lock_key,lock_token)' in MAIN
    assert 'await _release_payment_side_effect_lock(user_lock_key,user_token)' in MAIN
    assert 'finally: await _release_payment_side_effect_lock(lock_key,lock_token)' not in MAIN


def test_expiry_notification_marker_is_committed_only_after_successful_delivery():
    block = MAIN[MAIN.index('async def expiry_notification_scheduler'):MAIN.index('@app.get("/api/me/subscription")')]
    assert 'sending_key=key+":sending"' in block
    assert 'nx=True,ex=300' in block
    assert 'resp=await client.post' in block
    assert 'if resp.status_code >= 400:' in block
    assert 'await redis_client.set(key,"1",ex=86400*7)' in block
    assert 'await redis_client.delete(sending_key)' in block
