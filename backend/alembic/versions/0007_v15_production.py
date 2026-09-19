"""v15 production hardening"""
from alembic import op
import sqlalchemy as sa
revision = "0007_v15_production"
down_revision = "0006_v14_security"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("backup_jobs", sa.Column("sha256", sa.String(length=64), nullable=True))
    op.add_column("backup_jobs", sa.Column("encrypted", sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_column("backup_jobs", "encrypted")
    op.drop_column("backup_jobs", "sha256")
