from alembic import op

revision = "0006_v14_security"
down_revision = "0005_v11_backups"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS recovery_codes_encrypted TEXT")
    op.execute("ALTER TABLE promotions ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE promotions ADD COLUMN IF NOT EXISTS exclusive BOOLEAN NOT NULL DEFAULT TRUE")
    op.execute("""CREATE TABLE IF NOT EXISTS auth_exchange_codes (
        id SERIAL PRIMARY KEY,
        code_hash VARCHAR(128) NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        used_at TIMESTAMP NULL,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_auth_exchange_codes_code_hash ON auth_exchange_codes(code_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_auth_exchange_codes_user_id ON auth_exchange_codes(user_id)")

def downgrade():
    op.execute("DROP TABLE IF EXISTS auth_exchange_codes")
