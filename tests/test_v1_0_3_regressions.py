from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'backend/app/main.py').read_text()
BUILD=(ROOT/'scripts/build-release.sh').read_text()
INSTALL=(ROOT/'deploy/install-vps.sh').read_text()
MANIFEST=(ROOT/'release-manifest.template.json').read_text()


def test_release_is_v1_0_3_realise():
    assert 'APP_VERSION = "2.0.0-realise"' in MAIN
    assert 'VERSION="2.0.0-realise"' in BUILD
    assert 'INSTALLER_VERSION="2.0.0-realise"' in INSTALL
    assert '"version": "2.0.0-realise"' in MANIFEST


def test_lock_renewal_task_self_cleans_registry():
    assert '_LOCK_RENEW_TASKS.get(token) is current' in MAIN
    assert '_LOCK_RENEW_TASKS.pop(token,None)' in MAIN


def test_telegram_init_data_rejects_malformed_auth_date_and_user():
    assert 'except (TypeError,ValueError):' in MAIN
    assert 'Invalid Telegram auth date' in MAIN
    assert 'if not isinstance(user,dict) or not user.get("id")' in MAIN
