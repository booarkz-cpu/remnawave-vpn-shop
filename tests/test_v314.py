"""3.1.4: concurrent Alembic boot must not kill the API container."""
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_version_314_is_first():
    main = (ROOT / "backend/app/main.py").read_text()
    assert main.index('APP_VERSION = "3.1.4"') < main.index('APP_VERSION = "3.1.3"')
    build = (ROOT / "scripts/build-release.sh").read_text()
    assert build.index('VERSION="3.1.4"') < build.index('VERSION="3.1.3"')
    assert build.index("remnawave_vpn_shop_v3_1_4_full_release.zip") < build.index("remnawave_vpn_shop_v3_1_3_full_release.zip")
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    assert installer.index('INSTALLER_VERSION="3.1.4"') < installer.index('INSTALLER_VERSION="3.1.3"')


def test_migration_boot_is_serialized():
    env = (ROOT / "backend/alembic/env.py").read_text()
    create_at = env.index("CREATE TABLE IF NOT EXISTS alembic_version")
    lock_at = env.index("pg_advisory_xact_lock(872663041314)")
    assert lock_at < create_at
    compose = (ROOT / "docker-compose.yml").read_text()
    worker = compose.split("  worker:", 1)[1].split("  bot:", 1)[0]
    assert "backend:" in worker
    assert "condition: service_healthy" in worker
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    assert "docker compose logs --tail=180 backend worker" in installer
    assert "normalize_tz" in installer
    assert "Europe/Moscow" in installer


def test_prompt_trims_prices_and_maps_moscow():
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    helpers = installer[installer.index("trim_spaces() {"): installer.index("prompt_required() {")]
    script = (
        "set -Eeuo pipefail\n"
        + helpers
        + "\nINSTALL_NONINTERACTIVE=1 PRICE_1='189 ' TZ_VALUE=Moscow\n"
        + "prompt PRICE_1 'Цена' '199'\n"
        + "printf 'PRICE:%s\\n' \"$PRICE_1\"\n"
        + "normalized_tz=\"$(normalize_tz \"$TZ_VALUE\")\"\n"
        + "printf 'TZ:%s\\n' \"$normalized_tz\"\n"
    )
    proc = subprocess.run(["bash", "-s"], input=script, text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stderr
    assert "PRICE:189" in proc.stdout
    assert "TZ:Europe/Moscow" in proc.stdout


def test_docs_describe_314_and_keep_313():
    readme = (ROOT / "README.md").read_text()
    instruction = (ROOT / "INSTRUCTION.md").read_text()
    notes = (ROOT / "RELEASE_NOTES_V3_1_4.md").read_text()
    steps = (ROOT / "INSTALL_STEPS.md").read_text()
    assert "3.1.4" in readme and "3.1.3" in readme
    assert instruction.count("## 9.18.") == 2
    assert "pg_advisory_xact_lock" in notes or "alembic_version" in notes
    assert "Русский" in notes and "English" in notes
    assert '"version": "3.1.4"' in steps
    assert '"version": "3.1.3"' in steps


def test_parallel_alembic_upgrade_survives_the_race():
    probe = subprocess.run(
        ["sudo", "-n", "-u", "postgres", "psql", "-c", "SELECT 1"],
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        pytest.skip("local postgres is not available")
    name = "vpnshop_race314"
    subprocess.run(
        [
            "sudo", "-n", "-u", "postgres", "psql",
            "-c", "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='migtest') THEN CREATE ROLE migtest LOGIN PASSWORD 'migtest'; END IF; END $$;",
            "-c", f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{name}' AND pid<>pg_backend_pid();",
            "-c", f"DROP DATABASE IF EXISTS {name}",
            "-c", f"CREATE DATABASE {name} OWNER migtest",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    env = os.environ.copy()
    env["DATABASE_URL"] = f"postgresql+asyncpg://migtest:migtest@127.0.0.1:5432/{name}"
    env["APP_SECRET"] = "x" * 32
    procs = [
        subprocess.Popen(
            ["python3", "-m", "alembic", "upgrade", "head"],
            cwd=ROOT / "backend",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for _ in range(2)
    ]
    outputs = [(proc.wait(timeout=60), proc.stdout.read() if proc.stdout else "") for proc in procs]
    subprocess.run(["sudo", "-n", "-u", "postgres", "psql", "-c", f"DROP DATABASE IF EXISTS {name}"], check=False, capture_output=True)
    failed = [text for code, text in outputs if code != 0]
    assert not failed, failed
