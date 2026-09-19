"""V2.0.0 product features: subscription lifecycle and gift codes.

Revision ID: 0032_v2_0_0_product_features
Revises: 0031_v1_0_0_idempotency_integrity
"""
from alembic import op
import sqlalchemy as sa

revision = "0032_v2_0_0_product_features"
down_revision = "0031_v1_0_0_idempotency_integrity"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("subscriptions", sa.Column("lifecycle_status", sa.String(length=32), nullable=False, server_default="active"))
    op.add_column("subscriptions", sa.Column("grace_until", sa.DateTime(), nullable=True))
    op.add_column("subscriptions", sa.Column("scheduled_cancel_at", sa.DateTime(), nullable=True))
    op.add_column("subscriptions", sa.Column("cancelled_at", sa.DateTime(), nullable=True))
    op.add_column("subscriptions", sa.Column("last_renewal_failure_at", sa.DateTime(), nullable=True))
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("jti_hash", sa.String(length=64), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("jti_hash", name="uq_user_sessions_jti_hash"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_jti_hash", "user_sessions", ["jti_hash"], unique=True)
    op.create_table(
        "gift_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_gift_codes_code"),
    )
    op.create_index("ix_gift_codes_code", "gift_codes", ["code"], unique=True)
    op.create_table(
        "gift_redemptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("gift_code_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("gift_code_id", "user_id", name="uq_gift_redemption_code_user"),
    )
    op.create_index("ix_gift_redemptions_gift_code_id", "gift_redemptions", ["gift_code_id"])
    op.create_index("ix_gift_redemptions_user_id", "gift_redemptions", ["user_id"])
    op.add_column("gift_redemptions", sa.Column("operation_key", sa.String(length=128), nullable=True))
    op.add_column("gift_redemptions", sa.Column("status", sa.String(length=32), nullable=False, server_default="processing"))
    op.add_column("gift_redemptions", sa.Column("remote_user_id", sa.String(length=255), nullable=True))
    op.add_column("gift_redemptions", sa.Column("expected_before_expires_at", sa.DateTime(), nullable=True))
    op.add_column("gift_redemptions", sa.Column("expected_after_expires_at", sa.DateTime(), nullable=True))
    op.add_column("gift_redemptions", sa.Column("error", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_gift_redemptions_operation_key", "gift_redemptions", ["operation_key"])


def downgrade():
    op.drop_constraint("uq_gift_redemptions_operation_key", "gift_redemptions", type_="unique")
    op.drop_column("gift_redemptions", "error")
    op.drop_column("gift_redemptions", "expected_after_expires_at")
    op.drop_column("gift_redemptions", "expected_before_expires_at")
    op.drop_column("gift_redemptions", "remote_user_id")
    op.drop_column("gift_redemptions", "status")
    op.drop_column("gift_redemptions", "operation_key")
    op.drop_index("ix_user_sessions_jti_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_gift_redemptions_user_id", table_name="gift_redemptions")
    op.drop_index("ix_gift_redemptions_gift_code_id", table_name="gift_redemptions")
    op.drop_table("gift_redemptions")
    op.drop_index("ix_gift_codes_code", table_name="gift_codes")
    op.drop_table("gift_codes")
    op.drop_column("subscriptions", "last_renewal_failure_at")
    op.drop_column("subscriptions", "cancelled_at")
    op.drop_column("subscriptions", "scheduled_cancel_at")
    op.drop_column("subscriptions", "grace_until")
    op.drop_column("subscriptions", "lifecycle_status")
