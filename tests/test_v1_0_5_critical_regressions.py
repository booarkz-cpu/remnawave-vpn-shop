from pathlib import Path

MAIN = Path("backend/app/main.py").read_text()


def test_fulfillment_reloads_payment_after_payment_lock_before_remote_side_effects():
    lock = 'payment_lock, token = await _acquire_payment_side_effect_lock(payment_id)'
    reload_marker = 'payment=(await db.execute(select(Payment).where(Payment.id==payment_id).with_for_update())).scalar_one_or_none()'
    remote_marker = 'rw=RemnawaveClient()'
    assert MAIN.index(lock) < MAIN.index(reload_marker) < MAIN.index(remote_marker)
    assert 'if payment.status in {"refunded", "refunded_pending_revoke", "creation_unknown"}:' in MAIN
    assert 'if payment.status != "paid":\n            raise RuntimeError("Payment is not confirmed")' in MAIN


def test_refund_and_fulfillment_share_payment_lock():
    assert 'await _acquire_payment_side_effect_lock(p.id)' in MAIN
    assert 'await _acquire_payment_side_effect_lock(payment_id)' in MAIN


def test_release_keeps_token_safe_cleanup():
    marker = 'if redis.call(\'get\', KEYS[1]) == ARGV[1] then return redis.call(\'del\', KEYS[1]) else return 0 end'
    assert marker in MAIN
