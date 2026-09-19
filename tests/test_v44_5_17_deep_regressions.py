from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / 'backend/app/main.py').read_text()


def test_refund_reconciliation_serializes_with_fulfillment():
    start = MAIN.index('async def refund_revoke_scheduler():')
    block = MAIN[start:MAIN.index('@app.post("/api/admin/refunds/{refund_id}/retry-revoke")', start)]
    assert 'payment_lock, payment_token = await _acquire_payment_side_effect_lock(p.id)' in block
    assert 'await _release_payment_side_effect_lock(payment_lock, payment_token)' in block


def test_refund_retry_revoke_serializes_with_fulfillment():
    start = MAIN.index('@app.post("/api/admin/refunds/{refund_id}/retry-revoke")')
    block = MAIN[start:MAIN.index('@app.post("/api/admin/refunds/{refund_id}/reconcile")', start)]
    assert 'payment_lock, payment_token = await _acquire_payment_side_effect_lock(p.id)' in block
    assert 'finally:' in block
    assert 'await _release_payment_side_effect_lock(payment_lock, payment_token)' in block


def test_reconciliation_only_reverses_referral_after_successful_revoke():
    start = MAIN.index('async def refund_revoke_scheduler():')
    block = MAIN[start:MAIN.index('@app.post("/api/admin/refunds/{refund_id}/retry-revoke")', start)]
    assert 'if r.status == "refunded"' in block
