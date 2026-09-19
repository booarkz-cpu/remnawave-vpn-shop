"""V44.5.15 safety integrity constraints.

Revision ID: 0029_v44_5_15_safety_integrity
Revises: 0028_v44_5_12_logic_integrity
"""
from alembic import op
import sqlalchemy as sa

revision = "0029_v44_5_15_safety_integrity"
down_revision = "0028_v44_5_12_logic_integrity"
branch_labels = None
depends_on = None

def upgrade():
    op.create_check_constraint(
        "ck_withdrawal_requests_amount_positive",
        "withdrawal_requests",
        sa.text("amount > 0"),
    )
    op.create_check_constraint(
        "ck_payout_transactions_amount_positive",
        "payout_transactions",
        sa.text("amount > 0"),
    )

def downgrade():
    op.drop_constraint("ck_payout_transactions_amount_positive", "payout_transactions", type_="check")
    op.drop_constraint("ck_withdrawal_requests_amount_positive", "withdrawal_requests", type_="check")
