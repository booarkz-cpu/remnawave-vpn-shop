"""V2.3.0 wallet balance, gift purchaser and bonus days."""
from alembic import op
import sqlalchemy as sa

revision = "0035_v2_3_0_wallet_gifts"
down_revision = "0034_v2_2_0_platform_features"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("wallet_balance", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("payments", sa.Column("purpose", sa.String(24), nullable=False, server_default="subscription"))
    op.add_column("payments", sa.Column("bonus_days", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("gift_codes", sa.Column("purchaser_user_id", sa.Integer(), nullable=True))
    op.add_column("gift_codes", sa.Column("idempotency_key", sa.String(128), nullable=True))
    op.create_index("ix_gift_codes_purchaser_user_id", "gift_codes", ["purchaser_user_id"])
    op.create_index("ix_gift_codes_idempotency_key", "gift_codes", ["idempotency_key"], unique=True)


def downgrade():
    op.drop_index("ix_gift_codes_idempotency_key", table_name="gift_codes")
    op.drop_index("ix_gift_codes_purchaser_user_id", table_name="gift_codes")
    op.drop_column("gift_codes", "idempotency_key")
    op.drop_column("gift_codes", "purchaser_user_id")
    op.drop_column("payments", "bonus_days")
    op.drop_column("payments", "purpose")
    op.drop_column("users", "wallet_balance")
