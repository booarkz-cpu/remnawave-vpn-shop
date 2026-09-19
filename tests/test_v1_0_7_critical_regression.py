from pathlib import Path


def test_release_version_and_critical_fulfill_user_recheck_present():
    main = Path('backend/app/main.py').read_text()
    assert 'APP_VERSION = "2.0.0-realise"' in main
    assert 'User is deleted or no longer available for fulfillment' in main
    assert 'select(User).where(User.id==user.id).with_for_update()' in main


def test_fulfill_rechecks_user_after_user_lock_before_payment_lock():
    main = Path('backend/app/main.py').read_text()
    lock_pos = main.index('user_lock,user_token=await _acquire_user_fulfillment_lock(user.id,ttl=300)')
    recheck_pos = main.index('select(User).where(User.id==user.id).with_for_update()', lock_pos)
    payment_pos = main.index('payment_lock, token = await _acquire_payment_side_effect_lock(payment_id)', recheck_pos)
    assert lock_pos < recheck_pos < payment_pos
