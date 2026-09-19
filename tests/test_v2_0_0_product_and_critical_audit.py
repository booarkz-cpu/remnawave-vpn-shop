from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'backend/app/main.py').read_text()
MODELS=(ROOT/'backend/app/models.py').read_text()
MIG=(ROOT/'backend/alembic/versions/0032_v2_0_0_product_features.py').read_text()
BUILD=(ROOT/'scripts/build-release.sh').read_text()
MANIFEST=(ROOT/'release-manifest.template.json').read_text()


def test_v2_release_contract_and_migration_head():
    assert 'APP_VERSION = "2.0.0-realise"' in MAIN
    assert 'VERSION="2.0.0-realise"' in BUILD
    assert '0032_v2_0_0_product_features' in BUILD
    assert '"version": "2.0.0-realise"' in MANIFEST


def test_subscription_lifecycle_has_server_side_state_and_lock():
    assert 'lifecycle_status' in MODELS
    assert 'grace_until' in MODELS
    block=MAIN[MAIN.index('@app.post("/api/me/subscription/lifecycle")'):MAIN.index('@app.post("/api/me/gifts/redeem")')]
    assert '_acquire_user_fulfillment_lock' in block
    assert 'with_for_update()' in block
    assert 'cancel_scheduled' in block
    assert 'grace' in block


def test_gift_redemption_is_unique_and_serialized():
    assert 'class GiftCode' in MODELS
    assert 'class GiftRedemption' in MODELS
    assert 'UniqueConstraint("gift_code_id", "user_id", name="uq_gift_redemption_code_user")' in MODELS
    block=MAIN[MAIN.index('@app.post("/api/me/gifts/redeem")'):MAIN.index('@app.post("/api/me/referral/apply")')]
    assert 'with_for_update()' in block
    assert 'GiftRedemption' in block
    assert 'IntegrityError' in block


def test_refund_dry_run_does_not_mutate_state():
    block=MAIN[MAIN.index('@app.get("/api/admin/refunds/{refund_id}/dry-run")'):MAIN.index('@app.get("/api/admin/security/risk-summary")')]
    assert 'return {"safe_to_execute"' in block
    assert 'await db.commit()' not in block
    assert 'planned_actions' in block


def test_customer_360_is_server_side_authorized():
    block=MAIN[MAIN.index('@app.get("/api/admin/customers/{user_id}/360")'):MAIN.index('@app.get("/api/admin/refunds/{refund_id}/dry-run")')]
    assert 'require_permission("users.read")' in block
    assert 'SupportTicket' in block
    assert 'FraudSignal' in block


def test_critical_paths_still_recheck_user_after_user_lock():
    block=MAIN[MAIN.index('async def fulfill(payment_id:int, db:AsyncSession, existing_user_lock_token: str|None = None):'):MAIN.index('async def payment_by_provider')]
    assert block.index('select(User).where(User.id==user.id).with_for_update()') < block.index('payment_lock, token = await _acquire_payment_side_effect_lock(payment_id)')
    assert 'if not user or user.deleted_at is not None' in block


def test_lock_order_is_user_then_payment_on_refund():
    block=MAIN[MAIN.index('@app.post("/api/admin/refunds/{refund_id}/execute")'):MAIN.index('@app.post("/api/admin/refunds/{refund_id}/retry-revoke")')]
    assert block.index('_acquire_user_fulfillment_lock') < block.index('_acquire_payment_side_effect_lock')


def test_migration_creates_lifecycle_and_gift_tables():
    for needle in ['op.add_column("subscriptions"', 'op.create_table(\n        "gift_codes"', 'op.create_table(\n        "gift_redemptions"']:
        assert needle in MIG


def test_user_sessions_make_logout_and_global_revocation_real_server_side_controls():
    assert 'class UserSession' in MODELS
    assert 'async def create_user_session' in MAIN
    assert 'UserSession.jti_hash' in MAIN
    assert '@app.post("/api/me/security/revoke-all")' in MAIN
    assert 'revoked_at.is_(None)' in MAIN


def test_expired_subscription_has_remote_revoke_retry_state():
    block=MAIN[MAIN.index('async def subscription_lifecycle_scheduler()'):MAIN.index('async def expiry_notification_scheduler()')]
    assert 'revoke_pending' in block
    assert 'disable_user' in block
    assert '_acquire_user_fulfillment_lock' in block


def test_gift_activation_is_remote_idempotent_operation_not_local_only_credit():
    block=MAIN[MAIN.index('@app.post("/api/me/gifts/redeem")'):MAIN.index('@app.post("/api/me/referral/apply")')]
    assert 'operation_key=f"gift:{code.id}:{user.id}"' in block
    assert 'extend_idempotent' in block
    assert 'create_user' in block
    assert 'redemption.status="completed"' in block
