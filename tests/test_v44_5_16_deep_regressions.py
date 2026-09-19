from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/"backend/app/main.py").read_text()
MODELS=(ROOT/"backend/app/models.py").read_text()
MIG=(ROOT/"backend/alembic/versions/0030_v44_5_16_privacy_and_refund_integrity.py").read_text()
BUILD=(ROOT/"scripts/build-release.sh").read_text()

def test_deleted_users_are_persistently_invalidated_for_user_tokens():
    assert 'deleted_at: Mapped[datetime|None]' in MODELS
    assert 'if not user or user.deleted_at is not None' in MAIN
    assert 'user.deleted_at=datetime.utcnow()' in MAIN

def test_privacy_delete_serializes_against_fulfillment_and_revokes_devices():
    block=MAIN[MAIN.index('@app.delete("/api/me/privacy/account")'):MAIN.index('@app.get("/api/admin/monitoring")')]
    assert '_acquire_user_fulfillment_lock(user.id)' in block
    assert "UPDATE user_devices SET status='revoked'" in block
    assert 'method.status="deleted"' in block

def test_fulfillment_rejects_deleted_accounts():
    start=MAIN.index('async def fulfill(payment_id:int')
    block=MAIN[start:MAIN.index('async def payment_by_provider',start)]
    assert 'user.deleted_at is not None' in block

def test_refund_and_fulfillment_share_a_payment_side_effect_lock():
    assert 'async def _acquire_payment_side_effect_lock' in MAIN
    execute=MAIN[MAIN.index('@app.post("/api/admin/refunds/{refund_id}/execute")'):MAIN.index('@app.post("/api/admin/refunds/{refund_id}/retry-revoke")')]
    reconcile=MAIN[MAIN.index('@app.post("/api/admin/refunds/{refund_id}/reconcile")'):MAIN.index('# ---------- Admin API ----------')]
    assert '_acquire_payment_side_effect_lock(p.id)' in execute
    assert '_acquire_payment_side_effect_lock(p.id)' in reconcile
    assert 'payment.status != "paid" or payment.fulfillment_terminal' in MAIN

def test_v44_5_16_migration_adds_deleted_at():
    assert '0030_v44_5_16_privacy_and_refund_integrity' in MIG
    assert '0029_v44_5_15_safety_integrity' in MIG
    assert 'add_column("users"' in MIG

def test_release_tooling_is_44_5_16():
    assert 'VERSION="1.0.0-realise"' in BUILD
    assert 'remnawave_vpn_shop_v1_0_0_realise_deep_audited_fixed.zip' in BUILD
    assert '0030_v44_5_16_privacy_and_refund_integrity' in BUILD
