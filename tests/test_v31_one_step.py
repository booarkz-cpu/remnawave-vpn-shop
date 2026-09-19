from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_one_step_wrapper_exists_and_execs_installer():
    p = ROOT / "install.sh"
    text = p.read_text()
    assert "deploy/install-vps.sh" in text
    assert p.stat().st_mode & 0o111


def test_installer_generates_lockfiles_and_never_requires_manual_lockfile_editing():
    text = (ROOT / "deploy/install-vps.sh").read_text()
    assert "npm install --package-lock-only" in text
    assert "package-lock.json" in text
    assert "npm ci" not in text


def test_pinned_images_are_written_to_compose_env():
    text = (ROOT / "scripts/pin-images.sh").read_text()
    assert "cat .env.images >> \"$tmp\"" in text
    assert "awk '!/^(REDIS_IMAGE|POSTGRES_IMAGE|CADDY_IMAGE)=/'" in text


def test_money_inputs_use_decimal():
    main = (ROOT / "backend/app/main.py").read_text()
    models = (ROOT / "backend/app/models.py").read_text()
    payments = (ROOT / "backend/app/payments.py").read_text()
    assert "price: Decimal = Field" in main
    assert "price: Mapped[Decimal]" in models
    assert "expected_amount: Decimal" in payments


def test_installer_version_is_v33():
    text = (ROOT / "deploy/install-vps.sh").read_text()
    assert "43.1.0-production" in text
