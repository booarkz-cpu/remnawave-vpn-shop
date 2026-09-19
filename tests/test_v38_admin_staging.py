from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_admin_telegram_and_staging_routes():
    s=(ROOT/'backend/app/main.py').read_text()
    assert 'telegram_id:int|None' in s
    assert '/api/admin/auth/telegram' in s
    assert '/api/admin/staging-e2e/config' in s
    assert '/api/admin/staging-e2e/run' in s
    assert 'encrypt_secret(json.dumps(data' in s

def test_admin_model_and_migration_have_telegram_id():
    model=(ROOT/'backend/app/models.py').read_text()
    mig=(ROOT/'backend/alembic/versions/0016_v38_admin_staging.py').read_text()
    assert 'telegram_id: Mapped[int|None]' in model
    assert 'uq_admin_users_telegram_id' in mig

def test_admin_ui_has_russian_staging_and_telegram_controls():
    ui=(ROOT/'admin/src/main.tsx').read_text()
    assert 'Telegram ID' in ui
    assert 'Войти через Telegram' in ui
    assert 'Настройка боевого staging E2E' in ui
    assert '/api/admin/staging-e2e/run' in ui


def test_staging_isolation_and_runner_are_safe():
    main=(ROOT/'backend/app/main.py').read_text(); pay=(ROOT/'backend/app/payments.py').read_text(); docker=(ROOT/'backend/Dockerfile').read_text(); sh=(ROOT/'scripts/staging-e2e.sh').read_text()
    assert 'staging_confirmed' in main and 'production-платёжные credentials' in main
    assert 'staging_create_payment' in pay and 'Production settings are deliberately never consulted' in pay
    assert 'COPY scripts/staging-e2e.sh ./staging-e2e.sh' in docker
    assert '/api/internal/staging-e2e/payment' in sh and 'STAGING_RUNNER_TOKEN' in sh
