"""V44.5.12: enforce persisted business invariants for trials, promo counters and payments."""
from alembic import op
import sqlalchemy as sa

revision = "0028_v44_5_12_logic_integrity"
down_revision = "0027_v44_5_10_financial_integrity"
branch_labels = None
depends_on = None

def upgrade():
    op.create_check_constraint("ck_trial_grants_days_valid", "trial_grants", sa.text("days >= 1 AND days <= 30"))
    op.create_check_constraint("ck_promo_codes_reserved_nonnegative", "promo_codes", sa.text("reserved_count >= 0"))
    op.create_check_constraint("ck_promo_codes_used_nonnegative", "promo_codes", sa.text("used_count >= 0"))
    op.create_check_constraint("ck_payments_amount_positive", "payments", sa.text("amount > 0"))
    op.create_check_constraint("ck_payments_discount_nonnegative", "payments", sa.text("discount_amount >= 0"))

def downgrade():
    op.drop_constraint("ck_payments_discount_nonnegative", "payments", type_="check")
    op.drop_constraint("ck_payments_amount_positive", "payments", type_="check")
    op.drop_constraint("ck_promo_codes_used_nonnegative", "promo_codes", type_="check")
    op.drop_constraint("ck_promo_codes_reserved_nonnegative", "promo_codes", type_="check")
    op.drop_constraint("ck_trial_grants_days_valid", "trial_grants", type_="check")
