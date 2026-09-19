from alembic import op
revision="0005_v11_backups"
down_revision="0004_miniapp_editor"
branch_labels=None
depends_on=None

def upgrade():
    op.execute("CREATE TABLE IF NOT EXISTS backup_jobs (id SERIAL PRIMARY KEY, status VARCHAR(32) NOT NULL DEFAULT 'queued', filename VARCHAR(255), size_bytes BIGINT, error TEXT, created_at TIMESTAMP NOT NULL DEFAULT NOW(), finished_at TIMESTAMP)")

def downgrade():
    op.execute("DROP TABLE IF EXISTS backup_jobs")
