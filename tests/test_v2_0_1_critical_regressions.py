from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "backend/app/main.py"
MAIN = MAIN_PATH.read_text()


def _function(name: str):
    tree = ast.parse(MAIN)
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function not found: {name}")


def test_telegram_login_declares_request_dependency():
    fn = _function("telegram_auth")
    assert "request" in {a.arg for a in fn.args.args}
    assert any(isinstance(n, ast.Name) and n.id == "request" and isinstance(n.ctx, ast.Load) for n in ast.walk(fn))


def test_yandex_exchange_declares_request_dependency():
    fn = _function("auth_exchange")
    assert "request" in {a.arg for a in fn.args.args}
    assert any(isinstance(n, ast.Name) and n.id == "request" and isinstance(n.ctx, ast.Load) for n in ast.walk(fn))


def test_release_scripts_are_executable():
    for rel in ("install.sh", "scripts/build-release.sh", "scripts/staging-e2e.sh"):
        assert (ROOT / rel).stat().st_mode & 0o111, rel
