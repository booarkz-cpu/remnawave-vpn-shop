"""3.1.6: admin, Mini App and cabinet nginx must serve HTTP on a read-only root."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_version_316_is_first():
    main = (ROOT / "backend/app/main.py").read_text()
    assert main.index('APP_VERSION = "3.1.6"') < main.index('APP_VERSION = "3.1.5"')
    build = (ROOT / "scripts/build-release.sh").read_text()
    assert build.index('VERSION="3.1.6"') < build.index('VERSION="3.1.5"')
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    assert installer.index('INSTALLER_VERSION="3.1.6"') < installer.index('INSTALLER_VERSION="3.1.5"')


def test_nginx_uses_tmp_and_is_mounted():
    nginx = (ROOT / "deploy/nginx/nginx.conf").read_text()
    default = (ROOT / "deploy/nginx/default.conf").read_text()
    assert "pid /tmp/nginx/nginx.pid;" in nginx
    assert "client_body_temp_path /tmp/nginx/client_temp;" in nginx
    assert "try_files $uri $uri/ /index.html;" in default
    for app in ("admin", "miniapp", "cabinet"):
        assert (ROOT / app / "nginx.conf").read_text() == nginx
        assert (ROOT / app / "default.conf").read_text() == default
        dockerfile = (ROOT / app / "Dockerfile").read_text()
        assert "COPY nginx.conf /etc/nginx/nginx.conf" in dockerfile
    compose = (ROOT / "docker-compose.yml").read_text()
    caddy = compose.split("  caddy:", 1)[1]
    for name in ("admin", "miniapp", "cabinet"):
        block = compose.split(f"  {name}:", 1)[1].split(f"  {'miniapp' if name == 'admin' else 'cabinet' if name == 'miniapp' else 'caddy'}:", 1)[0]
        assert "./deploy/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" in block
        assert "/tmp/nginx/client_temp" in block
        assert "condition: service_healthy" in caddy.split(f"{name}:", 1)[1].split("\n", 3)[1]


def test_docs_describe_316():
    notes = (ROOT / "RELEASE_NOTES_V3_1_6.md").read_text()
    instruction = (ROOT / "INSTRUCTION.md").read_text()
    assert "client_temp" in notes or "/tmp/nginx" in notes
    assert "502" in notes
    assert instruction.count("## 9.20.") == 2
