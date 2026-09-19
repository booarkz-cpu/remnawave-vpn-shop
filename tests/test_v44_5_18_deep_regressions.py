from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "backend/app/main.py").read_text()
PAYMENTS = (ROOT / "backend/app/payments.py").read_text()
REQ = (ROOT / "backend/requirements.txt").read_text()
BUILD = (ROOT / "scripts/build-release.sh").read_text()


def _block(start_marker, end_marker):
    start = MAIN.index(start_marker)
    return MAIN[start:MAIN.index(end_marker, start)]


def test_yookassa_webhook_binds_only_after_verified_order_metadata():
    block = _block('@app.post("/api/webhooks/yookassa")', '@app.post("/api/webhooks/platega")')
    assert 'if order_id and order_id != p.order_id: raise HTTPException(403,"Order mismatch")' in block
    verify = 'await YooKassaProvider().verify_succeeded(pid,Decimal(str(p.amount)),p.currency,p.order_id)'
    assert verify in block
    assert block.index(verify) < block.index('await bind_provider_payment_id(db,p,pid)')


def test_all_webhooks_ignore_late_success_for_refunded_payments():
    for provider, marker, end in [
        ('yookassa', '@app.post("/api/webhooks/yookassa")', '@app.post("/api/webhooks/platega")'),
        ('platega', '@app.post("/api/webhooks/platega")', '@app.post("/api/webhooks/rollypay")'),
        ('rollypay', '@app.post("/api/webhooks/rollypay")', '# ---------- Reliability, sessions, analytics, referrals ----------'),
    ]:
        block = _block(marker, end)
        assert 'p.status in {"refunded", "refunded_pending_revoke"}' in block
        assert 'payment_already_refunded' in block


def test_provider_verification_can_validate_immutable_order_id():
    assert 'expected_order_id: str|None = None' in PAYMENTS
    assert 'metadata") or {}).get("order_id")' in PAYMENTS
    assert 'd.get("payload") or d.get("Payload")' in PAYMENTS
    assert 'd.get("order_id") or ""' in PAYMENTS


def test_admin_retry_rejects_refunded_payment():
    block = _block('@app.post("/api/admin/payments/{payment_id}/retry")', '# ---------- V32 Operations / Monitoring / Fraud / Privacy ----------')
    assert 'p.status in {"refunded", "refunded_pending_revoke"}' in block
    assert 'Refunded payment cannot be fulfilled' in block


def test_release_is_44_5_20_and_build_has_yaml_dependency():
    assert 'VERSION="1.0.0-realise"' in BUILD
    assert 'remnawave_vpn_shop_v1_0_0_realise_deep_audited_fixed.zip' in BUILD
    assert 'PyYAML==6.0.3' in REQ


def test_auto_renew_serializes_paid_transition_with_payment_side_effect_lock():
    block = _block('async def auto_renew_scheduler():', 'async def reconciliation_scheduler():')
    assert block.count('payment_lock, payment_token = await _acquire_payment_side_effect_lock') >= 2
    assert 'existing.status in {"refunded", "refunded_pending_revoke"}' in block
    assert 'p.status in {"refunded", "refunded_pending_revoke"}' in block


def test_reconciliation_passes_immutable_order_to_provider_verification():
    block = _block('async def reconciliation_scheduler():', '@app.get("/api/me/subscription")')
    assert 'verify_succeeded(p.provider_payment_id,Decimal(str(p.amount)),p.currency,p.order_id)' in block
