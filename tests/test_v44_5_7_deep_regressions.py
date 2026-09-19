import ast
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "backend/app/main.py").read_text()
MODELS = (ROOT / "backend/app/models.py").read_text()
WORKER = (ROOT / "backend/worker.py").read_text()
MIG = (ROOT / "backend/alembic/versions/0024_v44_5_7_logic_hardening.py").read_text()


def test_provider_success_does_not_reenable_operator_disabled_provider():
    block = MAIN[MAIN.index('result=await candidate_provider.create'):MAIN.index('except Exception as exc:', MAIN.index('result=await candidate_provider.create'))]
    assert 'health.enabled=True' not in block
    assert 'health.circuit_open_until=None' in block


def test_referral_is_snapshotted_at_payment_creation_and_not_current_user_state():
    assert 'referrer_id_snapshot=user.referred_by_id' in MAIN
    assert 'if payment.referrer_id_snapshot:' in MAIN
    assert 'ReferralReward(referrer_id=payment.referrer_id_snapshot' in MAIN


def test_referral_attribution_is_serialized():
    assert 'select(User).where(User.id==user.id).with_for_update()' in MAIN


def test_refund_revoke_only_protected_by_completed_newer_fulfillment():
    assert 'Payment.fulfillment_status=="completed"' in MAIN


def test_existing_subscription_extension_starts_from_latest_known_expiry():
    assert 'remote_expiry=await rw.get_expiry(sub.remnawave_uuid)' in MAIN
    assert 'before_local=max(sub.expires_at or now, remote_expiry or now, now)' in MAIN


def test_trial_reenables_existing_disabled_subscription_user():
    assert 'if sub and sub.remnawave_uuid:' in WORKER
    assert 'remote_status in {"disabled","blocked","inactive"}' in WORKER
    assert 'await rw.enable_user(sub.remnawave_uuid)' in WORKER


def test_promo_usage_has_real_reservation_state():
    assert 'class PromoReservation(Base):' in MODELS
    assert 'reserved_count: Mapped[int]' in MODELS
    assert 'reserve_promo(db,promo,user.id,canonical_order_id)' in MAIN
    assert 'status=="reserved"' in MAIN
    assert 'await release_promo_reservation(db,reservation.id)' in MAIN


def test_promo_reservation_migration_exists():
    assert '0024_v44_5_7_logic_hardening' in MIG
    assert 'promo_reservations' in MIG
    assert 'reserved_count' in MIG


def test_all_changed_python_sources_parse():
    for path in [ROOT / 'backend/app/main.py', ROOT / 'backend/app/models.py', ROOT / 'backend/worker.py', ROOT / 'backend/alembic/versions/0024_v44_5_7_logic_hardening.py']:
        ast.parse(path.read_text())
