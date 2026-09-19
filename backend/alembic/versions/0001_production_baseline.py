"""production baseline: shop schema, admin RBAC/MFA and payment hardening"""
from alembic import op

revision="0001_production_baseline"
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    statements = """
    CREATE TABLE IF NOT EXISTS users (
      id SERIAL PRIMARY KEY, telegram_id BIGINT NOT NULL UNIQUE, username VARCHAR(255), created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS ix_users_telegram_id ON users(telegram_id);
    CREATE TABLE IF NOT EXISTS plans (
      id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL, price NUMERIC(12,2) NOT NULL, duration_days INTEGER NOT NULL,
      traffic_limit_gb INTEGER, device_limit INTEGER, remnawave_profile_id VARCHAR(255), enabled BOOLEAN NOT NULL DEFAULT TRUE
    );
    CREATE TABLE IF NOT EXISTS payments (
      id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, plan_id INTEGER NOT NULL, provider VARCHAR(32) NOT NULL,
      provider_payment_id VARCHAR(255) NOT NULL UNIQUE, order_id VARCHAR(255) NOT NULL UNIQUE,
      amount NUMERIC(12,2) NOT NULL, currency VARCHAR(3) NOT NULL DEFAULT 'RUB', status VARCHAR(32) NOT NULL DEFAULT 'pending',
      checkout_url TEXT, created_at TIMESTAMP NOT NULL DEFAULT NOW(), paid_at TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_payments_user_id ON payments(user_id);
    CREATE INDEX IF NOT EXISTS ix_payments_provider_payment_id ON payments(provider_payment_id);
    ALTER TABLE payments ADD COLUMN IF NOT EXISTS order_id VARCHAR(255);
    ALTER TABLE payments ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'RUB';
    ALTER TABLE payments ADD COLUMN IF NOT EXISTS checkout_url TEXT;
    ALTER TABLE payments ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP;
    UPDATE payments SET order_id='legacy-'||id WHERE order_id IS NULL;
    ALTER TABLE payments ALTER COLUMN order_id SET NOT NULL;
    CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments(order_id);
    CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_order_id ON payments(order_id);
    CREATE TABLE IF NOT EXISTS subscriptions (
      id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, plan_id INTEGER NOT NULL, remnawave_uuid VARCHAR(255),
      subscription_url TEXT, expires_at TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_subscriptions_user_id ON subscriptions(user_id);
    CREATE TABLE IF NOT EXISTS admin_users (
      id SERIAL PRIMARY KEY, email VARCHAR(320) NOT NULL UNIQUE, password_hash VARCHAR(512) NOT NULL,
      role VARCHAR(32) NOT NULL DEFAULT 'viewer', totp_secret_encrypted TEXT, mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
      disabled BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMP NOT NULL DEFAULT NOW(), last_login_at TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_admin_users_email ON admin_users(email);
    CREATE TABLE IF NOT EXISTS audit_logs (
      id SERIAL PRIMARY KEY, action VARCHAR(100) NOT NULL, actor VARCHAR(320) NOT NULL DEFAULT 'system',
      target VARCHAR(200), details TEXT, created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);
    """.split(";")
    for statement in statements:
        statement = statement.strip()
        if statement:
            op.execute(statement)

def downgrade():
    op.execute("DROP TABLE IF EXISTS audit_logs, admin_users, subscriptions, payments, plans, users CASCADE")
