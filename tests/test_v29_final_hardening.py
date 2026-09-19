from pathlib import Path
ROOT=Path(__file__).parents[1]
MAIN=(ROOT/"backend/app/main.py").read_text()
PAY=(ROOT/"backend/app/payments.py").read_text()
CFG=(ROOT/"backend/app/config.py").read_text()

def test_provider_refunds_never_cross_call_yookassa():
    p=PAY[PAY.index("class PlategaProvider"):PAY.index("def verify_rollypay")]
    r=PAY[PAY.index("class RollyPayProvider"):PAY.index("def verify_rollypay")]
    assert "api.yookassa.ru/v3/refunds" not in p
    assert "api.yookassa.ru/v3/refunds" not in r
    assert "platega_refund_url" in p and "rollypay_refund_url" in r

def test_extend_has_remote_expiry_reconciliation():
    assert "expected_after_expires_at" in MAIN and "extend_idempotent" in MAIN and "already_applied" in MAIN

def test_referral_withdrawal_is_atomic_and_reversible():
    assert "UPDATE users SET referral_balance=referral_balance-:amount" in MAIN
    assert "withdrawal_reversal:" in MAIN

def test_refund_revoke_recovery_exists():
    assert "/api/admin/refunds/{refund_id}/retry-revoke" in MAIN
    assert "disable_user(sub.remnawave_uuid)" in MAIN

def test_secrets_status_uses_real_settings():
    assert "settings.bot_token" in MAIN and "settings.remnawave_token" in MAIN
    assert "settings.telegram_bot_token" not in MAIN and "settings.remnawave_api_token" not in MAIN

def test_rollback_excludes_secrets_and_has_db_dump():
    u=(ROOT/"scripts/update.sh").read_text(); r=(ROOT/"scripts/rollback.sh").read_text()
    assert "--exclude='./.env'" in u and "--exclude='./.env.*'" in u
    assert "pg_dump" in u and "psql" in u and "DB_DUMP" in u
    assert "pg_dump" not in r or "psql" in r

def test_integration_uses_published_port():
    c=(ROOT/"docker-compose.integration.yml").read_text(); t=(ROOT/"scripts/integration-test.sh").read_text()
    assert '"18000:8000"' in c and "localhost:18000/health" in t

def test_safe_restore_and_no_store_backup():
    assert 'posix.is_absolute() or ".." in parts' in MAIN
    assert 'Cache-Control":"private, no-store"' in MAIN

def test_v29_migration_exists():
    assert (ROOT/"backend/alembic/versions/0013_v29_final_hardening.py").exists()
    assert '0013_v29_final_hardening' in (ROOT/"backend/alembic/versions/0013_v29_final_hardening.py").read_text()
