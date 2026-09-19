"""V44.5.8: immutable subscription entitlement snapshots and retry-safe provisioning."""
from alembic import op
import sqlalchemy as sa

revision = "0025_v44_5_8_entitlement_idempotency"
down_revision = "0024_v44_5_7_logic_hardening"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("subscriptions", sa.Column("traffic_limit_gb_snapshot", sa.Integer(), nullable=True))
    op.add_column("subscriptions", sa.Column("device_limit_snapshot", sa.Integer(), nullable=True))
    op.add_column("subscriptions", sa.Column("remnawave_profile_id_snapshot", sa.String(255), nullable=True))


def downgrade():
    op.drop_column("subscriptions", "remnawave_profile_id_snapshot")
    op.drop_column("subscriptions", "device_limit_snapshot")
    op.drop_column("subscriptions", "traffic_limit_gb_snapshot")
