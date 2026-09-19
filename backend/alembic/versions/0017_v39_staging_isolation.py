"""V39 staging payment isolation and E2E runner hardening."""
from alembic import op
import sqlalchemy as sa
revision="0017_v39_staging_isolation"
down_revision="0016_v38_admin_staging"
branch_labels=None
depends_on=None

def upgrade():
    # Keep staging credentials in the existing encrypted app_settings store; this migration
    # only records an explicit schema/version marker for safe upgrades.
    op.execute("SELECT 1")

def downgrade():
    op.execute("SELECT 1")
