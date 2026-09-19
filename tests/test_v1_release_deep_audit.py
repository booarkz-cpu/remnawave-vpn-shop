from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'backend/app/main.py').read_text()
MODELS=(ROOT/'backend/app/models.py').read_text()
BUILD=(ROOT/'scripts/build-release.sh').read_text()
INSTALL=(ROOT/'deploy/install-vps.sh').read_text()
MANIFEST=(ROOT/'release-manifest.template.json').read_text()
MIG=(ROOT/'backend/alembic/versions/0031_v1_0_0_idempotency_integrity.py').read_text()


def test_release_version_and_migration_head():
    assert 'APP_VERSION = "1.0.0-realise"' in MAIN
    assert 'VERSION="1.0.0-realise"' in BUILD
    assert 'INSTALLER_VERSION="1.0.0-realise"' in INSTALL
    assert '"version": "1.0.0-realise"' in MANIFEST
    assert '0032_v2_0_0_product_features' in BUILD


def test_payment_idempotency_is_database_enforced():
    assert 'UniqueConstraint("user_id", "idempotency_key", name="uq_payments_user_idempotency_key")' in MODELS
    assert 'uq_payments_user_idempotency_key' in MIG
    assert 'GROUP BY user_id, idempotency_key' in MIG
    assert 'migration refused: duplicate payment idempotency keys exist' in MIG


def test_long_running_locks_use_renewable_helper():
    assert 'await _acquire_redis_lock(lock_key,ttl=300,conflict_message="Payment creation is already in progress")' in MAIN
    assert 'await _acquire_user_fulfillment_lock(user.id,ttl=300)' in MAIN
    assert 'await _acquire_redis_lock("lock:backup",ttl=3600,conflict_message="A backup is already running")' in MAIN
    assert 'await _acquire_redis_lock("lock:maintenance",ttl=1800,conflict_message="Maintenance operation already in progress")' in MAIN
    assert 'await _acquire_redis_lock(f"lock:auto-renew:user:{user.id}:{date_key}",ttl=900,conflict_message="Auto-renew is already in progress")' in MAIN


def test_identity_registration_has_cross_process_serialization():
    assert 'pg_advisory_xact_lock(:key)' in MAIN
    assert 'hashlib.sha256(str(telegram_id).encode())' in MAIN
    assert 'hashlib.sha256(yid.encode())' in MAIN
    assert 'Yandex profile has no stable identifier' in MAIN
    assert '1300000001' in MAIN
    assert '1300000002' in MAIN
