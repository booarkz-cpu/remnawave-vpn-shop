"""marketing: promotions, promo codes, ads, broadcasts and payment discount metadata"""
from alembic import op

revision="0003_marketing"
down_revision="0002_cms_yandex"
branch_labels=None
depends_on=None

def upgrade():
    op.execute("ALTER TABLE users ALTER COLUMN telegram_id DROP NOT NULL")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS original_amount NUMERIC(12,2)")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS promo_code VARCHAR(64)")
    op.execute("CREATE TABLE IF NOT EXISTS promotions (id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL, kind VARCHAR(16) NOT NULL DEFAULT 'percent', value NUMERIC(12,2) NOT NULL, plan_ids JSONB, starts_at TIMESTAMP, ends_at TIMESTAMP, enabled BOOLEAN NOT NULL DEFAULT TRUE, description TEXT NOT NULL DEFAULT '')")
    op.execute("CREATE TABLE IF NOT EXISTS promo_codes (id SERIAL PRIMARY KEY, code VARCHAR(64) NOT NULL UNIQUE, kind VARCHAR(16) NOT NULL DEFAULT 'percent', value NUMERIC(12,2) NOT NULL, plan_ids JSONB, starts_at TIMESTAMP, ends_at TIMESTAMP, usage_limit INTEGER, used_count INTEGER NOT NULL DEFAULT 0, enabled BOOLEAN NOT NULL DEFAULT TRUE)")
    op.execute("CREATE TABLE IF NOT EXISTS advertisements (id SERIAL PRIMARY KEY, title VARCHAR(255) NOT NULL, text TEXT NOT NULL DEFAULT '', image_url TEXT, button_text VARCHAR(100), button_url TEXT, starts_at TIMESTAMP, ends_at TIMESTAMP, enabled BOOLEAN NOT NULL DEFAULT TRUE, sort_order INTEGER NOT NULL DEFAULT 0)")
    op.execute("CREATE TABLE IF NOT EXISTS broadcasts (id SERIAL PRIMARY KEY, text TEXT NOT NULL, image_url TEXT, button_text VARCHAR(100), button_url TEXT, status VARCHAR(32) NOT NULL DEFAULT 'queued', target VARCHAR(32) NOT NULL DEFAULT 'all', sent_count INTEGER NOT NULL DEFAULT 0, failed_count INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMP NOT NULL DEFAULT NOW(), finished_at TIMESTAMP)")

def downgrade():
    op.execute("DROP TABLE IF EXISTS broadcasts, advertisements, promo_codes, promotions")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS promo_code")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS discount_amount")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS original_amount")
