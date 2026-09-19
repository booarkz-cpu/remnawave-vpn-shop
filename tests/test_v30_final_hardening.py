from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_rollypay_refund_generates_nonce():
    text=(ROOT/"backend/app/payments.py").read_text()
    assert 'nonce=str(uuid.uuid4())' in text
    assert '"X-Nonce":nonce' in text

def test_frontend_builds_require_lockfiles():
    for d in ("admin","miniapp"):
        text=(ROOT/d/"Dockerfile").read_text()
        assert 'COPY package*.json ./' in text
        assert 'npm ci' in text and 'npm install --package-lock=false' in text

def test_rollback_is_fail_closed():
    text=(ROOT/"scripts/rollback.sh").read_text()
    assert 'DATABASE SNAPSHOT' in text or 'Database snapshot is required' in text
    assert 'docker compose up -d db redis' in text
    assert 'doctor.sh' in text

def test_update_does_not_ignore_doctor_failure():
    text=(ROOT/"scripts/update.sh").read_text()
    assert './scripts/doctor.sh || true' not in text

def test_worker_identity_is_unique():
    text=(ROOT/"backend/worker.py").read_text()
    assert 'settings.worker_role}:{socket.gethostname()}:{os.getpid()}' in text

def test_digest_pinning_is_enforced():
    text=(ROOT/"scripts/preflight.sh").read_text()
    assert 'REDIS_IMAGE=.*@sha256:' in text
    assert 'POSTGRES_IMAGE=.*@sha256:' in text
    assert 'CADDY_IMAGE=.*@sha256:' in text

def test_release_signature_verifier_exists():
    assert (ROOT/"scripts/verify-release.sh").exists()
    assert (ROOT/"release-manifest.template.json").exists()
    text=(ROOT/"scripts/verify-release.sh").read_text()
    assert 'DEFAULT_MANIFEST' in text and '_manifest.json' in text

def test_v30_migration_exists():
    assert (ROOT/"backend/alembic/versions/0014_v30_final_hardening.py").exists()
