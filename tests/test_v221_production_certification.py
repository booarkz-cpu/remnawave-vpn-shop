from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def test_payment_provider_never_uses_unpinned_http_client():
    tree = ast.parse((ROOT / "backend/app/payments.py").read_text())
    offenders=[]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "AsyncClient":
            offenders.append(node.lineno)
    assert offenders == [], f"Direct httpx.AsyncClient bypasses DNS pinning at lines {offenders}"


def test_payment_module_routes_outbound_http_through_pinned_helper():
    text=(ROOT/"backend/app/payments.py").read_text()
    assert "def _public_client(timeout_seconds: int)" in text
    assert "_pinned_public_http_client(timeout_seconds)" in text
    assert "_public_client(20)" in text
    assert "_public_client(10)" in text


def test_release_verifier_is_not_hardcoded_to_historical_artifact():
    text=(ROOT/"scripts/verify-release.sh").read_text()
    assert "remnawave_vpn_shop_v40_production.zip" not in text
    assert "find . -maxdepth 1 -type f -name 'remnawave_vpn_shop_*.zip'" in text
    assert "hashlib.sha256()" in text


def test_auto_renew_advertises_only_implemented_provider():
    text=(ROOT/"backend/app/main.py").read_text()
    assert '"supported_providers":["yookassa"]' in text
