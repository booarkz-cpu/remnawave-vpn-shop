import ast
from pathlib import Path


def test_payment_idempotency_reuse_is_explicitly_conflict_checked():
    src=Path('backend/app/main.py').read_text()
    assert 'Idempotency-Key уже использован для другого платежа' in src
    assert 'existing.plan_id != plan_id' in src
    assert 'final_amount=Decimal(str(existing.amount))' in src


def test_fulfillment_and_trial_keep_verified_remote_expiry():
    main=Path('backend/app/main.py').read_text()
    worker=Path('backend/worker.py').read_text()
    assert 'verified_expiry=extension.get("expires_at")' in main
    assert 'sub.expires_at=max(expected_after,verified_expiry or expected_after)' in main
    assert 'verified_expiry=extension.get("expires_at")' in worker
    assert 'sub.expires_at=max(after,verified_expiry or after)' in worker
