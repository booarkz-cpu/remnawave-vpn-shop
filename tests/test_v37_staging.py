from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_staging_e2e_runner_exists_and_is_safe():
    p=ROOT/'scripts'/'staging-e2e.sh'
    s=p.read_text()
    assert p.exists() and p.stat().st_mode & 0o111
    assert 'STAGING_REMNAWAVE_TOKEN' in s
    assert 'STAGING_RUNNER_TOKEN' in s
    assert all(x in s for x in ('yookassa','platega','rollypay'))
    assert 'https://*)' in s
    assert 'set -Eeuo pipefail' in s

def test_provider_endpoints_are_configurable_and_rolly_sandbox_supported():
    cfg=(ROOT/'backend/app/config.py').read_text()
    pay=(ROOT/'backend/app/payments.py').read_text()
    assert 'yookassa_api_url' in cfg and 'platega_api_url' in cfg and 'rollypay_api_url' in cfg
    assert 'rollypay_test_mode' in cfg
    assert 'payload["test"] = True' in pay
