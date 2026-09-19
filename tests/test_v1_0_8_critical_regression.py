from pathlib import Path

MAIN = Path('backend/app/main.py').read_text()


def _block(start_marker, end_marker):
    start = MAIN.index(start_marker)
    end = MAIN.index(end_marker, start)
    return MAIN[start:end]


def test_confirm_and_fulfill_rechecks_payment_under_locks_before_paid_transition():
    block = _block('async def _confirm_and_fulfill_payment', 'async def fulfill(')
    assert block.index('_acquire_user_fulfillment_lock(seed.user_id,ttl=300)') < block.index('_acquire_payment_side_effect_lock(payment_id)')
    assert 'select(Payment).where(Payment.id==payment_id).with_for_update()' in block
    assert 'if confirmed.status in {"refunded","refunded_pending_revoke","creation_unknown"}' in block
    assert 'confirmed.status="paid"' in block
    assert 'await fulfill(payment_id,db,existing_user_lock_token=user_token)' in block


def test_reconciliation_paths_use_atomic_confirmation_helper_instead_of_reviving_stale_payment():
    admin = _block('@app.post("/api/admin/payments/reconcile")', '@app.post("/api/admin/payments/{payment_id}/retry")')
    scheduler = _block('async def reconciliation_scheduler()', 'async def expiry_notification_scheduler()')
    assert '_confirm_and_fulfill_payment(p.id,db)' in admin
    assert 'p.status="paid"' not in admin
    assert '_confirm_and_fulfill_payment(p.id,db)' in scheduler
    assert 'p.status="paid"' not in scheduler


def test_all_success_webhooks_delegate_paid_transition_to_atomic_helper():
    for provider, end in [
        ('yookassa', '@app.post("/api/webhooks/platega")'),
        ('platega', '@app.post("/api/webhooks/rollypay")'),
        ('rollypay', '# ---------- Reliability, sessions, analytics, referrals ----------'),
    ]:
        block = _block(f'@app.post("/api/webhooks/{provider}")', end)
        assert '_confirm_and_fulfill_payment(p.id,db)' in block
        assert 'p.status="paid"' not in block
        assert 'p.status in {"refunded", "refunded_pending_revoke"}' in block
