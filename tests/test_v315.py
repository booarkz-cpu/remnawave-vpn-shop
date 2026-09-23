"""3.1.5: nginx frontends must start on a read-only root filesystem."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_version_315_is_first():
    main = (ROOT / "backend/app/main.py").read_text()
    assert main.index('APP_VERSION = "3.1.5"') < main.index('APP_VERSION = "3.1.4"')
    build = (ROOT / "scripts/build-release.sh").read_text()
    assert build.index('VERSION="3.1.5"') < build.index('VERSION="3.1.4"')
    assert build.index("remnawave_vpn_shop_v3_1_5_full_release.zip") < build.index("remnawave_vpn_shop_v3_1_4_full_release.zip")
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    assert installer.index('INSTALLER_VERSION="3.1.5"') < installer.index('INSTALLER_VERSION="3.1.4"')


def test_nginx_frontends_have_writable_cache_and_pid():
    compose = (ROOT / "docker-compose.yml").read_text()
    bounds = (("admin", "miniapp"), ("miniapp", "cabinet"), ("cabinet", "caddy"))
    for name, nxt in bounds:
        block = compose.split(f"  {name}:", 1)[1].split(f"  {nxt}:", 1)[0]
        assert "read_only: true" in block
        assert "/var/cache/nginx" in block
        assert "/run" in block
        assert "/tmp" in block
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    assert "docker compose logs --tail=80 admin miniapp cabinet" in installer
    assert "vm.overcommit_memory=1" in installer
    assert "restarting" in installer


def test_docs_describe_315_and_keep_314():
    notes = (ROOT / "RELEASE_NOTES_V3_1_5.md").read_text()
    instruction = (ROOT / "INSTRUCTION.md").read_text()
    steps = (ROOT / "INSTALL_STEPS.md").read_text()
    assert "client_temp" in notes
    assert "Русский" in notes and "English" in notes
    assert "3.1.4" in notes
    assert instruction.count("## 9.19.") == 2
    assert '"version": "3.1.5"' in steps
    assert '"version": "3.1.4"' in steps
