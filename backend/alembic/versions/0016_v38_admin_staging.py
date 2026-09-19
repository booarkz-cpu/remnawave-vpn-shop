"""Admin Telegram IDs and web-managed staging E2E settings."""
from alembic import op
import sqlalchemy as sa
revision="0016_v38_admin_staging"
down_revision="0015_v32_operations"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("admin_users", sa.Column("telegram_id", sa.BigInteger(), nullable=True))
    op.create_unique_constraint("uq_admin_users_telegram_id", "admin_users", ["telegram_id"])
    op.create_index("ix_admin_users_telegram_id", "admin_users", ["telegram_id"])

def downgrade():
    op.drop_index("ix_admin_users_telegram_id", table_name="admin_users")
    op.drop_constraint("uq_admin_users_telegram_id", "admin_users", type_="unique")
    op.drop_column("admin_users", "telegram_id")
