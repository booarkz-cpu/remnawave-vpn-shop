"""3.0.1 critical audit contracts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_301_is_current_and_documented():
    main = (ROOT / "backend/app/main.py").read_text()
    notes = (ROOT / "RELEASE_NOTES_V3_0_1.md").read_text()
    readme = (ROOT / "README.md").read_text()
    security = (ROOT / "SECURITY.md").read_text()
    instruction = (ROOT / "INSTRUCTION.md").read_text()
    assert main.index('APP_VERSION = "3.0.1"') < main.index('APP_VERSION = "3.0.0-realise"')
    assert main.index('APP_VERSION = "3.0.0-realise"') < main.index('APP_VERSION = "2.13.0"')
    assert "3.0.1" in notes and "Русский" in notes and "English" in notes
    assert "3.0.1" in readme and "3.0.0-realise" in readme
    assert "3.0.1" in security and "decrypt_secret" in security
    assert "9.13" in instruction
    assert "backend.app.security" not in main


def test_wallet_spend_requires_a_client_key_and_blocks_a_second_debit():
    main = (ROOT / "backend/app/main.py").read_text()
    spend = main[main.index("async def wallet_spend"): main.index("async def purchase_gift")]
    assert 'if not idem or len(idem)>128: raise HTTPException(400,"Idempotency-Key is required")' in spend
    assert "uuid.uuid4()" not in spend
    assert "Повторное списание с баланса заблокировано" in spend
    assert "timedelta(seconds=30)" in spend
    gift = main[main.index("async def purchase_gift"): main.index("async def redeem_gift")]
    assert gift.index("with_for_update") < gift.index('code="GIFT_"')
    create = main[main.index("async def create_payment"): main.index("async def _renew_redis_lock")]
    assert "lock:checkout-intent:" in create
    assert 'if existing.plan_id != plan_id' in create
