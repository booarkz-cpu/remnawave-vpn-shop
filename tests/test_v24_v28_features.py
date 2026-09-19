from pathlib import Path
ROOT=Path(__file__).parents[1]
MAIN=(ROOT/'backend/app/main.py').read_text()
MODELS=(ROOT/'backend/app/models.py').read_text()
SEC=(ROOT/'backend/app/security.py').read_text()
WORKER=(ROOT/'backend/worker.py').read_text()
COMPOSE=(ROOT/'docker-compose.yml').read_text()

def test_v24_reconciliation_and_refunds():
    assert 'payment.reconciliation' in MAIN
    assert 'class RefundRequest' in MODELS
    assert '/api/admin/payments/{payment_id}/refund-request' in MAIN
    assert '/api/admin/refunds/{refund_id}/mark-refunded' in MAIN

def test_v25_secret_rotation_and_security():
    assert 'app_secret_previous' in SEC
    assert 'APP_SECRET_PREVIOUS' in (ROOT/'.env.example').read_text()
    assert (ROOT/'scripts/rotate-secrets.sh').exists()
    assert 'no-new-privileges:true' in COMPOSE

def test_v25_worker_lease():
    assert 'class WorkerState' in MODELS
    assert 'worker:heartbeat:' in WORKER
    assert '/api/admin/workers' in MAIN

def test_v26_customer_dashboard_and_support():
    assert '/api/me/dashboard' in MAIN
    assert '/api/me/support/tickets' in MAIN
    assert 'class SupportTicket' in MODELS
    assert 'Реферальная программа' in (ROOT/'miniapp/src/main.tsx').read_text()

def test_v27_referral_withdrawals():
    assert 'class WithdrawalRequest' in MODELS
    assert '/api/me/referral/withdrawals' in MAIN
    assert '/api/admin/referrals/withdrawals/{withdrawal_id}/approve' in MAIN

def test_v28_release_and_ci():
    assert 'class ReleaseRecord' in MODELS
    assert '/api/admin/releases/check' in MAIN
    assert (ROOT/'.github/workflows/ci.yml').exists()
    assert (ROOT/'scripts/integration-test.sh').exists()
    assert (ROOT/'scripts/rotate-secrets.sh').exists()

def test_v27_provider_refund_adapter():
    payments=(ROOT/'backend/app/payments.py').read_text()
    assert 'async def refund' in payments
    assert '/api/admin/refunds/{refund_id}/execute' in MAIN

def test_v28_release_is_not_latest_tagged():
    assert 'latest' not in COMPOSE
    assert 'caddy", "validate"' in COMPOSE

def test_v28_image_pinning_tooling():
    assert (ROOT/'scripts/pin-images.sh').exists()
    assert 'RepoDigests' in (ROOT/'scripts/pin-images.sh').read_text()
    assert 'REDIS_IMAGE' in COMPOSE and 'POSTGRES_IMAGE' in COMPOSE and 'CADDY_IMAGE' in COMPOSE
