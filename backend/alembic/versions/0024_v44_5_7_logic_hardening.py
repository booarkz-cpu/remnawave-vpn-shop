"""Harden referral attribution, promo reservations, and immutable payment metadata."""
from alembic import op
import sqlalchemy as sa

revision = "0024_v44_5_7_logic_hardening"
down_revision = "0023_v44_5_3_billing_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payments", sa.Column("referrer_id_snapshot", sa.Integer(), nullable=True))
    op.create_index("ix_payments_referrer_id_snapshot", "payments", ["referrer_id_snapshot"])

    op.add_column("promo_codes", sa.Column("reserved_count", sa.Integer(), nullable=False, server_default="0"))
    op.create_table(
        "promo_reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("promo_code_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.String(255), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="reserved"),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("order_id", name="uq_promo_reservations_order_id"),
        sa.UniqueConstraint("payment_id", name="uq_promo_reservations_payment_id"),
    )
    op.create_index("ix_promo_reservations_promo_code_id", "promo_reservations", ["promo_code_id"])
    op.create_index("ix_promo_reservations_user_id", "promo_reservations", ["user_id"])
    op.create_index("ix_promo_reservations_order_id", "promo_reservations", ["order_id"])
    op.create_index("ix_promo_reservations_payment_id", "promo_reservations", ["payment_id"])


def downgrade():
    op.drop_index("ix_promo_reservations_payment_id", table_name="promo_reservations")
    op.drop_index("ix_promo_reservations_order_id", table_name="promo_reservations")
    op.drop_index("ix_promo_reservations_user_id", table_name="promo_reservations")
    op.drop_index("ix_promo_reservations_promo_code_id", table_name="promo_reservations")
    op.drop_table("promo_reservations")
    op.drop_column("promo_codes", "reserved_count")
    op.drop_index("ix_payments_referrer_id_snapshot", table_name="payments")
    op.drop_column("payments", "referrer_id_snapshot")
