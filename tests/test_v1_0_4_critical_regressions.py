from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "backend/app/main.py").read_text()
BUILD = (ROOT / "scripts/build-release.sh").read_text()
INSTALL = (ROOT / "deploy/install-vps.sh").read_text()
MANIFEST = (ROOT / "release-manifest.template.json").read_text()

def test_release_is_v1_0_5_realise():
    assert 'APP_VERSION = "2.0.0-realise"' in MAIN
    assert 'VERSION="2.0.0-realise"' in BUILD
    assert 'INSTALLER_VERSION="2.0.0-realise"' in INSTALL
    assert '"version": "2.0.0-realise"' in MANIFEST

def test_fulfillment_uses_global_user_then_payment_lock_order():
    block=MAIN[MAIN.index('async def fulfill('):MAIN.index('async def payment_by_provider',MAIN.index('async def fulfill('))]
    assert block.index('await _acquire_user_fulfillment_lock') < block.index('await _acquire_payment_side_effect_lock(payment_id)')
    assert 'Global lock order: user -> payment' in block

def test_fulfillment_does_not_release_a_caller_owned_user_lock():
    block=MAIN[MAIN.index('async def fulfill('):MAIN.index('async def payment_by_provider',MAIN.index('async def fulfill('))]
    assert 'if user_token and not existing_user_lock_token:' in block
    assert 'if payment_lock and token:' in block
