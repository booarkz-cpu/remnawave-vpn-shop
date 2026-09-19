"""V22 P0-P2 hardening: fulfillment terminal state and auto-renew lifecycle"""
from alembic import op
import sqlalchemy as sa
revision = "0010_v22_hardening"
down_revision = "0009_v20_v21"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("payments", sa.Column("fulfillment_max_attempts", sa.Integer(), server_default="8", nullable=False))
    op.add_column("payments", sa.Column("fulfillment_terminal", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("auto_renew_methods", sa.Column("status", sa.String(32), server_default="active", nullable=False))
    op.add_column("auto_renew_methods", sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("auto_renew_methods", sa.Column("next_attempt_at", sa.DateTime()))
    op.create_index("ix_payments_fulfillment_retry", "payments", ["fulfillment_status", "next_retry_at"])
    op.create_index("ix_auto_renew_due", "auto_renew_methods", ["status", "next_attempt_at"])

def downgrade():
    op.drop_index("ix_auto_renew_due", table_name="auto_renew_methods")
    op.drop_index("ix_payments_fulfillment_retry", table_name="payments")
    op.drop_column("auto_renew_methods", "next_attempt_at")
    op.drop_column("auto_renew_methods", "failure_count")
    op.drop_column("auto_renew_methods", "status")
    op.drop_column("payments", "fulfillment_terminal")
    op.drop_column("payments", "fulfillment_max_attempts")
