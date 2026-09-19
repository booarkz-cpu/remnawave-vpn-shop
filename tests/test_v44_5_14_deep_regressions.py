from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/"backend/app/main.py").read_text()
RW=(ROOT/"backend/app/remnawave.py").read_text()
MIG=(ROOT/"backend/alembic/versions/0028_v44_5_12_logic_integrity.py").read_text()
BUILD=(ROOT/"scripts/build-release.sh").read_text()
INSTALLER=(ROOT/"deploy/install-vps.sh").read_text()


def test_trial_is_not_available_to_active_subscribers():
    block=MAIN[MAIN.index('@app.post("/api/me/trial")'):MAIN.index('@app.get("/api/public/config")')]
    assert 'Subscription.user_id==user.id' in block
    assert 'Subscription.expires_at>now' in block
    assert 'Пробный период недоступен при действующей подписке' in block


def test_remote_entitlement_update_clears_old_limits_and_profiles():
    block=RW[RW.index('async def update_entitlements'):RW.index('async def disable_user')]
    assert 'trafficLimitBytes' in block and 'if traffic_limit_gb is not None else 0' in block
    assert 'activeInternalSquads' in block and '[]' in block


def test_existing_remote_user_recovery_reenables_and_reapplies_entitlements():
    block=MAIN[MAIN.index('existing_remote and existing_remote.get("id")'):MAIN.index('else:\n                    expires=now+timedelta', MAIN.index('existing_remote and existing_remote.get("id")'))]
    assert 'await rw.enable_user(remote_id)' in block
    assert 'await rw.update_entitlements(remote_id,traffic_limit_gb,profile_id)' in block


def test_webhooks_can_bind_unknown_creation_to_provider_id_by_order_id():
    assert 'async def payment_by_provider_or_order' in MAIN
    assert 'bind_provider_payment_id(db,p,pid)' in MAIN
    assert 'metadata") or {}).get("order_id")' in MAIN
    assert 'payload_order or None' in MAIN
    assert 'order_id or None' in MAIN


def test_webhook_event_fallback_is_unique_per_payload():
    yookassa=MAIN[MAIN.index('@app.post("/api/webhooks/yookassa")'):MAIN.index('@app.post("/api/webhooks/platega")')]
    assert 'hashlib.sha256(raw).hexdigest()' in yookassa
    assert 'or d.get("event")' not in yookassa


def test_persisted_business_invariants_exist_in_latest_migration():
    assert 'revision = "0028_v44_5_12_logic_integrity"' in MIG
    for name in ['ck_trial_grants_days_valid','ck_promo_codes_reserved_nonnegative','ck_promo_codes_used_nonnegative','ck_payments_amount_positive','ck_payments_discount_nonnegative']:
        assert name in MIG


def test_release_points_to_44_5_15_and_latest_migration():
    assert 'VERSION="1.0.0-realise"' in BUILD
    assert 'remnawave_vpn_shop_v1_0_0_realise_deep_audited_fixed.zip' in BUILD
    assert "0030_v44_5_16_privacy_and_refund_integrity" in BUILD
    assert 'INSTALLER_VERSION="1.0.0-realise"' in INSTALLER


def test_payment_idempotency_is_resolved_before_enabled_plan_validation():
    block=MAIN[MAIN.index('@app.post("/api/payments/create")'):MAIN.index('async def fulfill', MAIN.index('@app.post("/api/payments/create")'))]
    assert block.index('existing=(await db.execute(select(Payment)') < block.index('plan=await db.get(Plan,plan_id)')
    assert 'if existing.plan_id != plan_id' in block

def test_provider_create_must_return_an_external_payment_id():
    block=MAIN[MAIN.index('@app.post("/api/payments/create")'):MAIN.index('async def fulfill', MAIN.index('@app.post("/api/payments/create")'))]
    assert 'if not result.get("id")' in block
    assert 'Payment provider returned no payment ID' in block


def test_cryptography_is_pinned_to_a_security_fixed_release():
    req=(ROOT/"backend/requirements.txt").read_text()
    assert "cryptography==50.0.1" in req
    assert "cryptography==46.0.4" not in req

def test_trial_treats_null_expiry_subscription_as_active():
    block=MAIN[MAIN.index('@app.post("/api/me/trial")'):MAIN.index('@app.get("/api/public/config")')]
    assert 'Subscription.expires_at.is_(None)' in block
    assert 'or_(Subscription.expires_at.is_(None), Subscription.expires_at>now)' in block


def test_upload_endpoints_use_bounded_reads_for_chunked_requests():
    assert 'async def _read_upload_limited' in MAIN
    background=MAIN[MAIN.index('@app.post("/api/admin/miniapp/background")'):MAIN.index('@app.delete("/api/admin/miniapp/background")')]
    images=MAIN[MAIN.index('@app.post("/api/admin/images")'):MAIN.index('@app.delete("/api/admin/images/{image_id}")')]
    assert '_read_upload_limited(file,8*1024*1024)' in background
    assert '_read_upload_limited(file,5*1024*1024)' in images
    assert 'data=await file.read()' not in background
    assert 'data=await file.read()' not in images


def test_security_sensitive_dependency_pins_are_current_fixed_lines():
    req=(ROOT/"backend/requirements.txt").read_text()
    assert 'PyJWT==2.13.0' in req
    assert 'python-multipart==0.0.31' in req
    assert 'paramiko==5.0.0' in req
    assert 'boto3==1.43.91' in req
    assert 'authlib==' not in req
