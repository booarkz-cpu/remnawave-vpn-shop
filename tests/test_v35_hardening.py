from pathlib import Path
ROOT=Path(__file__).parents[1]

def test_v37_version_and_release_metadata():
    assert 'APP_VERSION = "43.1.0-production"' in (ROOT/'backend/app/main.py').read_text()
    assert 'INSTALLER_VERSION="43.1.0-production"' in (ROOT/'deploy/install-vps.sh').read_text()
    build=(ROOT/'scripts/build-release.sh').read_text()
    assert 'VERSION="43.1.0-production"' in build
    assert 'remnawave_vpn_shop_v39_production.zip' in build

def test_remnawave_uses_shared_http_pool_and_explicit_shutdown():
    m=(ROOT/'backend/app/remnawave.py').read_text()
    assert '_shared_client' in m
    assert 'max_keepalive_connections=20' in m
    assert 'close_shared_client' in m
    assert 'AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0))' not in m

def test_no_current_stale_v30_labels():
    for rel in ['PRODUCTION_CHECKLIST.md','docs_API.md','deploy/install-vps.sh']:
        text=(ROOT/rel).read_text()
        assert 'V30 Production Checklist' not in text
        assert '## V30 API' not in text
        assert 'Firewall V32:' not in text
