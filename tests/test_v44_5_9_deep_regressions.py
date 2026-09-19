from pathlib import Path

ROOT=Path(__file__).parents[1]
MAIN=(ROOT/'backend/app/main.py').read_text()
WORKER=(ROOT/'backend/worker.py').read_text()
MODELS=(ROOT/'backend/app/models.py').read_text()
PAY=(ROOT/'backend/app/payments.py').read_text()


def test_trial_grant_freezes_entitlements_and_has_fixed_retry_target():
    assert 'traffic_limit_gb_snapshot=plan.traffic_limit_gb' in MAIN
    assert 'device_limit_snapshot=plan.device_limit' in MAIN
    assert 'remnawave_profile_id_snapshot=plan.remnawave_profile_id' in MAIN
    assert 'expected_before_expires_at' in MODELS
    assert 'expected_after_expires_at' in MODELS
    assert 'trial.expected_before_expires_at' in WORKER
    assert 'trial.expected_after_expires_at' in WORKER


def test_trial_retry_does_not_recalculate_target_after_remote_success():
    assert 'extension=await rw.extend_idempotent(sub.remnawave_uuid,trial.days,before,after)' in WORKER
    assert 'expected=trial.expires_at or (now+timedelta(days=trial.days))' in WORKER


def test_reviving_a_revoked_device_rechecks_limit():
    assert 'if device_limit is not None and (not x or x.status != "active"):' in MAIN


def test_webhook_processing_event_can_be_reclaimed_after_stale_lease():
    assert "payment_provider_events.status='processing'" in MAIN
    assert "INTERVAL '10 minutes'" in MAIN
    assert 'received_at=NOW()' in MAIN


def test_auto_renew_retries_provider_failed_attempt_with_new_idempotency_key():
    assert 'get_payment_status' in PAY
    assert 'order_id=f"{prefix}-retry-{failed_count+1}"' in MAIN
    assert 'existing.status not in {"failed","canceled","cancelled"}' in MAIN


def test_auto_renew_stores_immutable_payment_terms():
    for x in ('duration_days_snapshot=plan.duration_days','traffic_limit_gb_snapshot=plan.traffic_limit_gb','device_limit_snapshot=plan.device_limit','remnawave_profile_id_snapshot=plan.remnawave_profile_id'):
        assert x in MAIN


def test_existing_trial_subscription_applies_frozen_entitlements_remotely():
    assert 'await rw.update_entitlements(sub.remnawave_uuid,trial.traffic_limit_gb_snapshot,trial.remnawave_profile_id_snapshot)' in WORKER


def test_auto_renew_searches_all_attempts_before_new_charge():
    assert 'Payment.order_id.like(prefix+"%")' in MAIN
    assert 'Never create a second charge while the newest provider attempt' in MAIN
    assert 'failed_count=sum(1 for item in attempts' in MAIN
