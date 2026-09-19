from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'backend/app/main.py').read_text()
WORKER=(ROOT/'backend/worker.py').read_text()
BUILD=(ROOT/'scripts/build-release.sh').read_text()
INSTALL=(ROOT/'deploy/install-vps.sh').read_text()
MANIFEST=(ROOT/'release-manifest.template.json').read_text()


def test_release_is_v45():
    assert 'APP_VERSION = "1.0.0-realise"' in MAIN
    assert 'VERSION="1.0.0-realise"' in BUILD
    assert 'INSTALLER_VERSION="1.0.0-realise"' in INSTALL
    assert '"version": "1.0.0-realise"' in MANIFEST
    assert 'remnawave_vpn_shop_v1_0_0_realise_deep_audited_fixed.zip' in BUILD


def test_distributed_locks_are_renewed_until_release():
    assert '_LOCK_RENEW_TASKS' in MAIN
    assert 'async def _renew_redis_lock' in MAIN
    assert "redis.call('expire', KEYS[1], ARGV[2])" in MAIN
    assert 'asyncio.create_task(_renew_redis_lock(key,token,ttl))' in MAIN
    assert '_LOCK_RENEW_TASKS.pop(token,None)' in MAIN


def test_refund_revoke_retry_uses_same_payment_side_effect_lock():
    block=MAIN[MAIN.index('async def refund_revoke_scheduler'):MAIN.index('async def auto_renew_scheduler')]
    assert 'payment_lock,payment_token=await _acquire_payment_side_effect_lock(p.id)' in block
    assert '_release_payment_side_effect_lock(payment_lock,payment_token)' in block
    assert 'with_for_update())).scalar_one()' in block


def test_trial_worker_serializes_with_account_deletion():
    block=WORKER[WORKER.index('if job.kind=="trial"'):WORKER.index('elif job.kind=="fulfillment"')]
    assert 'main._acquire_user_fulfillment_lock(user.id,ttl=900)' in block
    assert 'user.deleted_at is not None' in block
    assert 'main._release_payment_side_effect_lock(user_lock,user_token)' in block


def test_auto_renew_serializes_with_account_deletion_and_rechecks_state():
    block=MAIN[MAIN.index('async def auto_renew_scheduler'):MAIN.index('async def reconciliation_scheduler')]
    assert 'main._acquire_user_fulfillment_lock' not in block  # same-module call must not be qualified
    assert '_acquire_user_fulfillment_lock(user.id,ttl=900)' in block
    assert 'select(User).where(User.id==user.id).with_for_update()' in block
    assert 'user.deleted_at is not None' in block
    assert 'not user.auto_renew_enabled' in block


def test_monitoring_transport_still_pins_dns_and_disables_proxy():
    assert 'transport=httpx.AsyncHTTPTransport(retries=0,trust_env=False)' in MAIN
    assert 'follow_redirects=False' in MAIN
    assert 'target=addresses[0]' in MAIN
    assert 'return await self._backend.connect_tcp(target,port' in MAIN


def test_chunked_requests_are_bounded_without_content_length():
    block=MAIN[MAIN.index('class SecurityHeadersMiddleware'):MAIN.index('_METRICS =')]
    assert 'async for chunk in request.stream()' in block
    assert 'total > MAX_REQUEST_BYTES' in block
    assert 'request._body=b"".join(body_parts)' in block
