"""V44.5.16 privacy session invalidation and refund/fulfillment integrity.

Revision ID: 0030_v44_5_16_privacy_and_refund_integrity
Revises: 0029_v44_5_15_safety_integrity
"""
from alembic import op
import sqlalchemy as sa

revision = "0030_v44_5_16_privacy_and_refund_integrity"
down_revision = "0029_v44_5_15_safety_integrity"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column("users", "deleted_at")
