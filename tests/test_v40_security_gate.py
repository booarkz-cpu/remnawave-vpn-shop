from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(rel): return (ROOT/rel).read_text(encoding="utf-8")

def test_admin_frontend_identifiers_are_valid_and_staging_secret_preservation_is_supported():
    s=read("admin/src/main.tsx")
    assert "function Workers(" in s and "function Jobs(" in s
    assert "<Рабочие процессы" not in s and "<Задачаs" not in s
    assert "сохранить текущий" in s

def test_production_payments_are_fail_closed_behind_staging_gate():
    s=read("backend/app/main.py")
    assert 'PRODUCTION_PAYMENTS_GATE_KEY="payments.production_gate"' in s
    assert "требуется успешный staging E2E" in s
    assert 'await set_setting(db,PRODUCTION_PAYMENTS_GATE_KEY,"0")' in s
    assert '@app.post("/api/admin/payments/production-gate")' in s

def test_staging_internal_endpoint_is_loopback_only():
    s=read("backend/app/main.py")
    assert 'client_host not in {"127.0.0.1","::1"}' in s

def test_admin_sessions_have_idle_timeout_and_user_agent_binding():
    s=read("backend/app/security.py")
    assert "timedelta(minutes=15)" in s
    assert "Admin session device changed" in s

def test_admin_auth_has_rate_limits_for_both_login_paths():
    s=read("backend/app/main.py")
    assert '"/api/admin/auth/login": 8' in s and '"/api/admin/auth/telegram": 8' in s
