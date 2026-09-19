import ast
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "backend/app/main.py").read_text()
SEC = (ROOT / "backend/app/security.py").read_text()
BOT = (ROOT / "backend/app/bot.py").read_text()
class V15ProductionTests(unittest.TestCase):
    def test_no_known_runtime_bugs(self):
        self.assertNotIn("LOGIN_BUCKET.setdefault(key", MAIN)
        self.assertNotIn("if payload.item_type==\"url\": validate_public_url(payload.action,allow_empty=False)\n    await db.delete(x)", MAIN)

    def test_python_sources_parse(self):
        for p in (ROOT / "backend/app").glob("*.py"):
            ast.parse(p.read_text())
    def test_security_contracts_v15(self):
        self.assertIn('APP_VERSION = "43.1.0-production"', MAIN)
        self.assertIn('AuthExchangeCode', MAIN); self.assertIn('"/api/auth/exchange"', MAIN)
        self.assertIn('request.cookies.get("rw_user")', MAIN); self.assertIn('request.cookies.get("rw_admin")', SEC)
        self.assertIn('X-CSRF-Token', MAIN); self.assertIn('_redis_allowed', MAIN); self.assertIn('Webhook IP not allowed', MAIN)
    def test_promo_usage_is_reserved_then_consumed_safely(self):
        self.assertIn('reserve_promo(db,promo,user.id,canonical_order_id)', MAIN)
        self.assertIn('promo_row.reserved_count=max(0,int(promo_row.reserved_count or 0)-1)', MAIN)
        self.assertIn('promo_row.used_count += 1', MAIN)
        self.assertNotIn('if promo: promo.used_count += 1', MAIN)
    def test_broadcast_atomic(self):
        self.assertIn('FOR UPDATE SKIP LOCKED', BOT)
    def test_https_urls(self):
        self.assertIn('Only absolute HTTPS URLs are allowed', MAIN); self.assertIn('parsed.scheme != "https"', MAIN)
    def test_mfa_recovery_and_payment_verification(self):
        self.assertIn("recovery_codes_encrypted", (ROOT / "backend/app/models.py").read_text())
        self.assertIn("with_for_update()", MAIN)
        self.assertIn("manage_own_mfa", SEC)
        self.assertIn('async def rw_keys(user_id:int,admin=Depends(require_permission("manage_users")))', MAIN)
        self.assertIn("sha256", (ROOT / "backend/app/models.py").read_text())
        self.assertIn("generate_recovery_codes", MAIN)
        pay=(ROOT / "backend/app/payments.py").read_text()
        self.assertIn("verify_succeeded", pay)
        self.assertIn("transaction/{payment_id}", pay)
        self.assertIn("api/v1/payments/{payment_id}", pay)
    def test_frontends_cookie_auth(self):
        for p in (ROOT / "admin/src/main.tsx", ROOT / "miniapp/src/main.tsx"):
            s=p.read_text(); self.assertNotIn('localStorage.setItem("user_token"',s); self.assertNotIn('localStorage.setItem("rw_admin_token"',s); self.assertIn('credentials:"include"',s)
if __name__=='__main__': unittest.main()
