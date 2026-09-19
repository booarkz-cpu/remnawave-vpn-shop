from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'backend/app/main.py').read_text()
MODELS=(ROOT/'backend/app/models.py').read_text()
SEC=(ROOT/'backend/app/security.py').read_text()
MAN=(ROOT/'release-manifest.template.json').read_text()
ADMIN=(ROOT/'admin/src/main.tsx').read_text()


def test_v41_feature_pack_contract():
    for name in ['FeatureFlag','PaymentProviderHealth','SecurityIncidentEvent','BackupVerification','WebAuthnCredential']:
        assert f'class {name}' in MODELS
    for route in ['/api/admin/v41/analytics','/api/admin/v41/diagnostics','/api/admin/v41/incidents','/api/admin/v41/providers','/api/admin/v41/crm/users','/api/admin/v41/features','/api/admin/v41/passkeys']:
        assert route in MAIN
    assert '0021_v43_hardening_docs' in MAN
    assert '43.1.0-production' in MAN
    assert 'feature_flags.manage' in SEC
    for label in ['Операции','Аналитика','Инциденты','Провайдеры','Клиенты','Функции','Ключи доступа']:
        assert label in ADMIN
