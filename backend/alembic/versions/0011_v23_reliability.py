"""V23 reliability: provisioning operations and webhook lifecycle"""
from alembic import op
import sqlalchemy as sa
revision = "0011_v23_reliability"
down_revision = "0010_v22_hardening"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("provisioning_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("operation_key", sa.String(128), nullable=False, unique=True),
        sa.Column("action", sa.String(32), nullable=False, server_default="provision"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("remote_user_id", sa.String(255)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime()),
    )
    op.create_index("ix_provisioning_operations_user_id", "provisioning_operations", ["user_id"])
    op.drop_constraint("uq_payment_provider_events_event_id", "payment_provider_events", type_="unique")
    op.create_unique_constraint("uq_payment_provider_events_provider_event", "payment_provider_events", ["provider", "event_id"])
    op.add_column("payment_provider_events", sa.Column("status", sa.String(32), nullable=False, server_default="verified"))
    op.add_column("payment_provider_events", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("payment_provider_events", sa.Column("last_error", sa.Text()))
    op.add_column("payment_provider_events", sa.Column("processed_at", sa.DateTime()))
    op.create_index("ix_payment_provider_events_status", "payment_provider_events", ["status"])

def downgrade():
    op.drop_index("ix_payment_provider_events_status", table_name="payment_provider_events")
    op.drop_constraint("uq_payment_provider_events_provider_event", "payment_provider_events", type_="unique")
    op.create_unique_constraint("uq_payment_provider_events_event_id", "payment_provider_events", ["event_id"])
    op.drop_column("payment_provider_events", "processed_at")
    op.drop_column("payment_provider_events", "last_error")
    op.drop_column("payment_provider_events", "attempts")
    op.drop_column("payment_provider_events", "status")
    op.drop_index("ix_provisioning_operations_user_id", table_name="provisioning_operations")
    op.drop_table("provisioning_operations")
