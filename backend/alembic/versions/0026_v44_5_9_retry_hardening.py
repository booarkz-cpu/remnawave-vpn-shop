"""V44.5.9: trial retry idempotency and entitlement snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "0026_v44_5_9_retry_hardening"
down_revision = "0025_v44_5_8_entitlement_idempotency"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("trial_grants", sa.Column("traffic_limit_gb_snapshot", sa.Integer(), nullable=True))
    op.add_column("trial_grants", sa.Column("device_limit_snapshot", sa.Integer(), nullable=True))
    op.add_column("trial_grants", sa.Column("remnawave_profile_id_snapshot", sa.String(255), nullable=True))
    op.add_column("trial_grants", sa.Column("expected_before_expires_at", sa.DateTime(), nullable=True))
    op.add_column("trial_grants", sa.Column("expected_after_expires_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("trial_grants", "expected_after_expires_at")
    op.drop_column("trial_grants", "expected_before_expires_at")
    op.drop_column("trial_grants", "remnawave_profile_id_snapshot")
    op.drop_column("trial_grants", "device_limit_snapshot")
    op.drop_column("trial_grants", "traffic_limit_gb_snapshot")
