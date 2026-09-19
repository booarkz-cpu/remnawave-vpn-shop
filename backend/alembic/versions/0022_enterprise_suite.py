"""Enterprise suite: devices, campaigns, rules, monitoring checks, trials, plan billing metadata."""
from alembic import op
import sqlalchemy as sa

revision = "0022_enterprise_suite"
down_revision = "0021_v43_hardening_docs"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("user_devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("device_key", sa.String(128), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False, server_default="Устройство"),
        sa.Column("platform", sa.String(64)), sa.Column("last_ip", sa.String(64)),
        sa.Column("last_seen_at", sa.DateTime()), sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("revoked_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_user_devices_user_status", "user_devices", ["user_id", "status"])
    op.create_table("campaigns",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="broadcast"), sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("audience", sa.JSON()), sa.Column("content", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("starts_at", sa.DateTime()), sa.Column("ends_at", sa.DateTime()), sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_campaigns_status", "campaigns", ["status"])
    op.create_table("automation_rules",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(255), nullable=False),
        sa.Column("event", sa.String(64), nullable=False), sa.Column("conditions", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("actions", sa.JSON(), nullable=False, server_default="{}"), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"), sa.Column("last_run_at", sa.DateTime()), sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_automation_rules_event_enabled", "automation_rules", ["event", "enabled"])
    op.create_table("monitoring_checks",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("url", sa.Text(), nullable=False),
        sa.Column("method", sa.String(8), nullable=False, server_default="GET"), sa.Column("interval_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="10"), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_status", sa.String(32)), sa.Column("last_latency_ms", sa.Integer()), sa.Column("last_error", sa.Text()), sa.Column("last_checked_at", sa.DateTime()),
        sa.Column("failure_streak", sa.Integer(), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_table("trial_grants",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), nullable=False, unique=True, index=True), sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False), sa.Column("status", sa.String(32), nullable=False, server_default="active"), sa.Column("granted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("expires_at", sa.DateTime()))

def downgrade():
    op.drop_table("trial_grants"); op.drop_table("monitoring_checks"); op.drop_table("automation_rules"); op.drop_table("campaigns"); op.drop_index("ix_user_devices_user_status", table_name="user_devices"); op.drop_table("user_devices")
