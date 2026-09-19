from pathlib import Path
ROOT=Path(__file__).parents[1]

def test_v36_version_and_installer():
    assert 'APP_VERSION = "43.1.0-production"' in (ROOT/'backend/app/main.py').read_text()
    assert 'INSTALLER_VERSION="43.1.0-production"' in (ROOT/'deploy/install-vps.sh').read_text()

def test_support_rbac_is_separated():
    sec=(ROOT/'backend/app/security.py').read_text()
    main=(ROOT/'backend/app/main.py').read_text()
    assert '"support.read"' in sec and '"support.write"' in sec
    assert 'require_permission("support.read")' in main
    assert 'require_permission("support.write")' in main

def test_traffic_endpoint_is_user_scoped():
    m=(ROOT/'backend/app/main.py').read_text()
    start=m.index('@app.get("/api/me/traffic")')
    end=m.index('@app.get("/api/me/privacy/export")', start)
    block=m[start:end]
    assert 'user_from_token(request,db)' in block
    assert 'Subscription.user_id==user.id' in block
    assert 'SupportTicket' not in block

def test_worker_health_uses_worker_state_not_role_heartbeat_key():
    m=(ROOT/'backend/app/main.py').read_text()
    start=m.index('@app.get("/api/admin/system/health")')
    end=m.index('@app.get("/api/admin/analytics")', start)
    block=m[start:end]
    assert 'WorkerState' in block
    assert 'last_seen_at>=cutoff' in block
    assert 'worker_count' in block
    assert 'worker:heartbeat:{settings.worker_role}' not in block

def test_no_v33_current_release_labels():
    for rel in ['admin/src/main.tsx','deploy/install-vps.sh','scripts/build-release.sh','release-manifest.template.json']:
        text=(ROOT/rel).read_text()
        assert 'V33' not in text and 'v33' not in text and '33.0.0-production' not in text
