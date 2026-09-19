"""Freeze purchased plan terms on payments and harden plan deletion."""
from alembic import op
import sqlalchemy as sa

revision="0023_v44_5_3_billing_snapshots"
down_revision="0022_enterprise_suite"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("payments", sa.Column("duration_days_snapshot", sa.Integer(), nullable=True))
    op.add_column("payments", sa.Column("traffic_limit_gb_snapshot", sa.Integer(), nullable=True))
    op.add_column("payments", sa.Column("device_limit_snapshot", sa.Integer(), nullable=True))
    op.add_column("payments", sa.Column("remnawave_profile_id_snapshot", sa.String(255), nullable=True))

def downgrade():
    op.drop_column("payments", "remnawave_profile_id_snapshot")
    op.drop_column("payments", "device_limit_snapshot")
    op.drop_column("payments", "traffic_limit_gb_snapshot")
    op.drop_column("payments", "duration_days_snapshot")
