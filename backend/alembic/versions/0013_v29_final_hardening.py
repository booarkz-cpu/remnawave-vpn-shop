"""V30 final hardening: idempotent extension metadata."""
from alembic import op
import sqlalchemy as sa
revision="0013_v29_final_hardening"
down_revision="0012_v24_v28_operations"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("provisioning_operations", sa.Column("expected_before_expires_at", sa.DateTime()))
    op.add_column("provisioning_operations", sa.Column("expected_after_expires_at", sa.DateTime()))
    op.create_index("ix_provisioning_operations_status", "provisioning_operations", ["status"])

def downgrade():
    op.drop_index("ix_provisioning_operations_status", table_name="provisioning_operations")
    op.drop_column("provisioning_operations", "expected_after_expires_at")
    op.drop_column("provisioning_operations", "expected_before_expires_at")
