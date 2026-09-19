import ast
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "backend/app/main.py").read_text()
MODELS = (ROOT / "backend/app/models.py").read_text()
WORKER = (ROOT / "backend/worker.py").read_text()
RW = (ROOT / "backend/app/remnawave.py").read_text()
MIG = (ROOT / "backend/alembic/versions/0027_v44_5_10_financial_integrity.py").read_text()


def test_refund_review_state_can_be_retried_safely():
    assert 'r.status not in {"requested","approved","review"}' in MAIN
    assert 'r.status="processing"' in MAIN


def test_recovery_code_consumption_locks_admin_row():
    assert 'select(AdminUser).where(AdminUser.email==payload.email.lower().strip()).with_for_update()' in MAIN


def test_subscription_uses_immutable_device_entitlement_snapshot():
    assert 'device_limit_snapshot: Mapped[int|None]' in MODELS
    assert 'device_limit=sub.device_limit_snapshot if sub.device_limit_snapshot is not None else (plan.device_limit if plan else None)' in MAIN
    assert 'sub.device_limit_snapshot=payment.device_limit_snapshot' in MAIN
    assert 'sub.traffic_limit_gb_snapshot=payment.traffic_limit_gb_snapshot' not in MAIN  # runtime uses resolved traffic value


def test_trial_copies_plan_entitlement_snapshot():
    assert 'sub.device_limit_snapshot=trial.device_limit_snapshot' in WORKER
    assert 'sub.traffic_limit_gb_snapshot=trial.traffic_limit_gb_snapshot' in WORKER


def test_provisioning_retries_reuse_persisted_target():
    assert 'persisted_before=op_row.expected_before_expires_at' in MAIN
    assert 'persisted_after=op_row.expected_after_expires_at' in MAIN
    assert 'await db.commit()' in MAIN[MAIN.index('persisted_before=op_row.expected_before_expires_at'):MAIN.index('extension=await rw.extend_idempotent', MAIN.index('persisted_before=op_row.expected_before_expires_at'))]


def test_remote_extension_rejects_unexpected_advanced_expiry():
    assert 'Remote expiry advanced unexpectedly; reconciliation is required' in RW


def test_existing_remote_user_receives_purchased_traffic_and_profile_terms():
    assert 'await rw.update_entitlements(sub.remnawave_uuid,traffic_limit_gb,profile_id)' in MAIN
    assert 'async def update_entitlements' in RW


def test_new_migration_is_current_head():
    assert 'revision = "0027_v44_5_10_financial_integrity"' in MIG
    assert 'down_revision = "0026_v44_5_9_retry_hardening"' in MIG


def test_sources_parse():
    for path in [ROOT / 'backend/app/main.py', ROOT / 'backend/app/models.py', ROOT / 'backend/app/remnawave.py', ROOT / 'backend/worker.py', ROOT / 'backend/alembic/versions/0027_v44_5_10_financial_integrity.py']:
        ast.parse(path.read_text())


def test_release_artifact_and_migration_head_are_current():
    build = (ROOT / 'scripts/build-release.sh').read_text()
    manifest = (ROOT / 'release-manifest.template.json').read_text()
    assert 'remnawave_vpn_shop_v1_0_0_realise_deep_audited_fixed.zip' in build
    assert '0030_v44_5_16_privacy_and_refund_integrity' in build
    assert 'remnawave_vpn_shop_v1_0_0_realise_deep_audited_fixed.zip' in manifest


def test_webhook_event_schema_matches_conflict_target():
    assert 'uq_payment_provider_events_provider_event' in MIG
    assert 'op.create_unique_constraint("uq_payment_provider_events_provider_event"' in MIG


def test_payment_provider_id_is_nullable_for_durable_external_intents():
    assert 'provider_payment_id: Mapped[str|None]' in MODELS
    assert 'provider_payment_id=None' in MAIN


def test_auto_renew_persists_intent_before_external_charge():
    marker = 'Persist the payment intent BEFORE the external charge.'
    assert marker in MAIN
    assert MAIN.index('db.add(payment); await db.flush()') < MAIN.index('result=await YooKassaProvider().charge_recurring', MAIN.index(marker))


def test_auto_renew_retries_same_durable_order_id():
    assert 'existing.status=="creating" and existing.provider_payment_id is None' in MAIN
    assert 'charge_recurring(Decimal(str(existing.amount)),existing.order_id' in MAIN


def test_interactive_checkout_persists_intent_before_provider_call():
    marker = 'Durable payment intent BEFORE the external provider call.'
    assert marker in MAIN
    block = MAIN[MAIN.index(marker):MAIN.index('async def fulfill', MAIN.index(marker))]
    assert block.index('db.add(payment_row)') < block.index('result=await candidate_provider.create')


def test_interactive_checkout_never_falls_back_after_ambiguous_creation():
    assert 'payment_row.status="creation_unknown"' in MAIN
    assert 'fallback_blocked' in MAIN
    assert 'Результат создания платежа не определён' in MAIN


def test_existing_uncertain_non_yookassa_payment_is_not_automatically_recharged():
    assert 'if existing.provider != "yookassa":' in MAIN
    assert 'Повторное списание заблокировано' in MAIN
