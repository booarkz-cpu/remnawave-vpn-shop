from pathlib import Path
ROOT=Path(__file__).parents[1]
MAIN=(ROOT/'backend/app/main.py').read_text()
MODELS=(ROOT/'backend/app/models.py').read_text()
MIG=(ROOT/'backend/alembic/versions/0027_v44_5_10_financial_integrity.py').read_text()

def test_v23_provisioning_operation_and_user_lock():
    assert 'class ProvisioningOperation' in MODELS
    assert 'lock:fulfill:user:' in MAIN
    assert 'get_user_by_username' in MAIN

def test_v23_webhook_verify_before_claim_and_provider_scoped_dedupe():
    assert 'ON CONFLICT (provider,event_id) DO UPDATE' in MAIN
    assert 'payment_provider_events.provider = EXCLUDED.provider' in MAIN
    assert MAIN.index('verify_succeeded(pid,Decimal(str(p.amount)),p.currency,p.order_id)') < MAIN.index('register_provider_event(db,"yookassa"', MAIN.index('async def yookassa_webhook'))
    assert 'uq_payment_provider_events_provider_event' in MIG

def test_v23_tar_restore_safety_and_recovery_mode():
    assert 'posix.is_absolute() or ".." in parts' in MAIN
    assert '_safe_extract_members(tar,{name},work)' in MAIN
    assert 'set_setting(fail_db,"restore_state","failed")' in MAIN

def test_v23_security_and_recovery_contracts():
    assert 'Metrics authentication is not configured' in MAIN
    assert 'WorkerState' in MAIN
    assert '/api/admin/recovery' in MAIN
    assert '/api/admin/incident-mode' in MAIN
    assert '/api/admin/referrals/reconcile' in MAIN

def test_v23_idempotency_and_validation():
    assert 'provider_name}:{user.id}:{plan.id}:{idem}' in MAIN
    assert 'raise HTTPException(400,"Invalid plan_id")' in MAIN
