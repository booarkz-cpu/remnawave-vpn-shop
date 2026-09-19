from pathlib import Path

MAIN = Path('backend/app/main.py').read_text()


def _block(start_marker, end_marker):
    start = MAIN.index(start_marker)
    end = MAIN.index(end_marker, start)
    return MAIN[start:end]


def test_confirm_helper_uses_confirmed_row_variable_and_never_undefined_name():
    block = _block('async def _confirm_and_fulfill_payment', 'async def fulfill(')
    assert 'if not confirmed:' in block
    assert 'confirmed_payment' not in block


def test_fulfill_reloads_user_for_update_even_when_caller_holds_user_lock():
    block = _block('async def fulfill(payment_id:int, db:AsyncSession, existing_user_lock_token: str|None = None):', 'async def payment_by_provider')
    lock_idx = block.index('user_token = existing_user_lock_token')
    reload_idx = block.index('select(User).where(User.id==user.id).with_for_update()')
    assert lock_idx < reload_idx
    assert 'if not existing_user_lock_token:' not in block[block.index('The first User read'):block.index('payment_lock, token = await _acquire_payment_side_effect_lock')]


def test_fulfill_rejects_deleted_user_before_payment_side_effect_lock():
    block = _block('async def fulfill(payment_id:int, db:AsyncSession, existing_user_lock_token: str|None = None):', 'async def payment_by_provider')
    assert block.index('if not user or user.deleted_at is not None') < block.index('payment_lock, token = await _acquire_payment_side_effect_lock(payment_id)')


def test_auto_renew_passes_existing_user_lock_to_fulfillment():
    block = _block('async def auto_renew_scheduler()', 'async def reconciliation_scheduler()')
    assert 'fulfill(existing.id,db,existing_user_lock_token=user_token)' in block
    assert 'fulfill(p.id,db,existing_user_lock_token=user_token)' in block
