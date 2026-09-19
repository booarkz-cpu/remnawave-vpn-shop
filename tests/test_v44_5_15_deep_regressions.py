from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "backend/app/main.py").read_text()
MODELS = (ROOT / "backend/app/models.py").read_text()
MIGRATIONS = ROOT / "backend/alembic/versions"


def test_privacy_delete_blocks_indefinite_subscription_and_revokes_remote_access():
    block = MAIN[MAIN.index('@app.delete("/api/me/privacy/account")'):MAIN.index('@app.get("/api/admin/monitoring")')]
    assert 'active.expires_at is None or active.expires_at>datetime.utcnow()' in block
    assert 'await RemnawaveClient().disable_user(active.remnawave_uuid)' in block
    assert 'active.remnawave_uuid=None' in block


def test_withdrawal_reject_cannot_restore_balance_after_payout_started():
    start = MAIN.index('@app.post("/api/admin/referrals/withdrawals/{withdrawal_id}/reject")')
    block = MAIN[start:MAIN.index('@app.post("/api/admin/referrals/withdrawals/{withdrawal_id}/approve")', start)]
    assert 'if x.status != "requested"' in block
    assert 'PayoutTransaction' in block
    assert 'double-spend' in block


def test_v44_5_16_migration_preserves_previous_head():
    path = MIGRATIONS / '0030_v44_5_16_privacy_and_refund_integrity.py'
    text = path.read_text()
    assert '0030_v44_5_16_privacy_and_refund_integrity' in text
    assert '0029_v44_5_15_safety_integrity' in text


def test_release_is_44_5_15():
    assert '1.0.0-realise' in (ROOT / 'backend/app/main.py').read_text()
    assert '1.0.0-realise' in (ROOT / 'scripts/build-release.sh').read_text()
    assert '1.0.0-realise' in (ROOT / 'deploy/install-vps.sh').read_text()
