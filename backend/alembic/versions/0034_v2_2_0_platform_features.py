"""V2.2.0 commercial platform: notifications, status page, deployments and promo controls."""
from alembic import op
import sqlalchemy as sa

revision = "0034_v2_2_0_platform_features"
down_revision = "0033_v2_1_0_production_hardening"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("promo_codes", sa.Column("first_purchase_only", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("promo_codes", sa.Column("max_uses_per_user", sa.Integer(), nullable=True))
    op.add_column("promo_codes", sa.Column("min_amount", sa.Numeric(12,2), nullable=True))
    op.add_column("promo_codes", sa.Column("referral_only", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(24), nullable=False, server_default="in_app"),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="queued"),
        sa.Column("dedupe_key", sa.String(160), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime()),
        sa.Column("sent_at", sa.DateTime()),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_notifications_user_dedupe"))
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_table("status_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="operational"),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_status_components_slug"))
    op.create_table("deployments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("previous_version", sa.String(64)),
        sa.Column("strategy", sa.String(24), nullable=False, server_default="canary"),
        sa.Column("traffic_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(24), nullable=False, server_default="planned"),
        sa.Column("error_rate_percent", sa.Numeric(6,3), nullable=False, server_default="0"),
        sa.Column("rollback_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime()))
    op.create_index("ix_deployments_version", "deployments", ["version"])
    op.create_index("ix_deployments_status", "deployments", ["status"])

def downgrade():
    op.drop_index("ix_deployments_status", table_name="deployments")
    op.drop_index("ix_deployments_version", table_name="deployments")
    op.drop_table("deployments")
    op.drop_table("status_components")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_column("promo_codes", "referral_only")
    op.drop_column("promo_codes", "min_amount")
    op.drop_column("promo_codes", "max_uses_per_user")
    op.drop_column("promo_codes", "first_purchase_only")
