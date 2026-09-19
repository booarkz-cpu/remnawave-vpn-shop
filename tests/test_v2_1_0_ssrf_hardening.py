from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / 'backend/app/main.py').read_text()
PAYMENTS = (ROOT / 'backend/app/payments.py').read_text()
STAGING = (ROOT / 'scripts/staging-e2e.sh').read_text()
BUILD = (ROOT / 'scripts/build-release.sh').read_text()
INSTALLER = (ROOT / 'deploy/install-vps.sh').read_text()


def test_release_identity_is_204():
    assert 'APP_VERSION = "2.1.0"' in MAIN
    assert 'VERSION="2.1.0"' in BUILD
    assert 'INSTALLER_VERSION="2.1.0"' in INSTALLER
    assert 'Remnawave VPN Shop — 2.1.0' in INSTALLER


def test_staging_urls_are_public_https_validated_before_persistence():
    block = MAIN[MAIN.index('async def update_staging_e2e_config'):MAIN.index('async def _run_staging_e2e')]
    assert 'validate_public_url(payload.public_base_url, allow_empty=False)' in block
    assert 'validate_public_url(payload.remnawave_url, allow_empty=False)' in block
    assert 'for provider_url in (payload.yookassa_api_url, payload.platega_api_url, payload.rollypay_api_url)' in block
    assert 'validate_public_url(provider_url, allow_empty=False)' in block


def test_staging_provider_requests_pin_dns_and_validate_endpoint():
    block = PAYMENTS[PAYMENTS.index('async def staging_create_payment'):]
    assert 'from .main import validate_public_url, _pinned_public_http_client' in block
    assert 'async with _pinned_public_http_client(20) as c:' in block
    assert block.count('validate_public_url(api_url, allow_empty=False)') == 3


def test_staging_runner_does_not_follow_redirects():
    assert '--max-redirs 0' in STAGING
    assert '--proto-redir "=https"' in STAGING
