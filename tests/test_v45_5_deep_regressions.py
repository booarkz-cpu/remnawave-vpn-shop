import ast
from pathlib import Path
SRC=Path('backend/app/main.py').read_text(); WORKER=Path('backend/worker.py').read_text()
def test_refund_creation_serializes_on_payment_row(): assert 'select(Payment).where(Payment.id==payment_id).with_for_update()' in SRC
def test_repurchase_reenables_disabled_remnawave_user(): assert 'await rw.enable_user(sub.remnawave_uuid)' in SRC and 'remote_status in {"disabled","blocked","inactive"}' in SRC
def test_trial_reactivates_disabled_remote_user(): assert 'await rw.enable_user(remote_id)' in WORKER
def test_auto_renew_payment_freezes_plan_terms():
    for x in ('duration_days_snapshot=plan.duration_days','traffic_limit_gb_snapshot=plan.traffic_limit_gb','device_limit_snapshot=plan.device_limit','remnawave_profile_id_snapshot=plan.remnawave_profile_id'): assert x in SRC
def test_public_provider_advertising_uses_real_routing_health(): assert 'payment_providers=await _payment_provider_order(db,None)' in SRC
def test_sources_parse(): ast.parse(SRC); ast.parse(WORKER)


def test_refund_retry_scheduler_uses_safe_revoke_and_reverses_reward():
    assert '_safe_revoke_for_refunded_payment(db,p,"system","subscription.revoked.refund.retry")' in SRC
    assert '_reverse_referral_reward_for_refund(db,p,"system")' in SRC

def test_manual_retry_reverses_referral_reward():
    needle='reversal_result=await _reverse_referral_reward_for_refund(db,p,admin.email)'
    assert needle in SRC

def test_refund_execution_is_retryable_after_ambiguous_review():
    assert 'r.status not in {"requested","approved","review"}' in SRC

def test_yookassa_refund_uses_deterministic_idempotency_key():
    payments=Path('backend/app/payments.py').read_text()
    assert 'idem=f"refund-{payment_id}"' in payments


def test_all_refund_side_effect_paths_follow_user_then_payment_lock_order():
    # Critical invariant: fulfillment is user -> payment. Every refund path that can
    # revoke a user's subscription must use the same order, otherwise concurrent
    # refund/fulfillment can deadlock and strand a paid/refunded payment.
    for name in ("refund_revoke_scheduler", "execute_refund", "retry_refund_revoke", "reconcile_refund"):
        start=SRC.index(f"async def {name}") if f"async def {name}" in SRC else SRC.index(f"@app.post(\"/api/admin/refunds/{{refund_id}}/{name.replace('retry_refund_revoke','retry-revoke')}\")")
        end=SRC.find("\nasync def ", start+1)
        if end == -1: end=len(SRC)
        block=SRC[start:end]
        assert block.find("_acquire_user_fulfillment_lock") < block.find("_acquire_payment_side_effect_lock")


def test_refund_scheduler_rechecks_payment_and_refund_after_both_locks():
    block=SRC[SRC.index('async def refund_revoke_scheduler'):SRC.index('async def auto_renew_scheduler')]
    assert 'select(Payment).where(Payment.id==p.id).with_for_update()' in block
    assert 'select(RefundRequest).where(RefundRequest.id==r.id).with_for_update()' in block
