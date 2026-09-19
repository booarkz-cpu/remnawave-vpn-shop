from alembic import op
revision="0002_cms_yandex"
down_revision="0001_production_baseline"
branch_labels=None
depends_on=None

def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS yandex_id VARCHAR(255)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_yandex_id ON users(yandex_id) WHERE yandex_id IS NOT NULL")
    op.execute("CREATE TABLE IF NOT EXISTS app_settings (key VARCHAR(100) PRIMARY KEY, value TEXT NOT NULL DEFAULT '')")
    op.execute("CREATE TABLE IF NOT EXISTS bot_menu_items (id SERIAL PRIMARY KEY, title VARCHAR(255) NOT NULL, action VARCHAR(255) NOT NULL, item_type VARCHAR(32) NOT NULL DEFAULT 'webapp', sort_order INTEGER NOT NULL DEFAULT 0, enabled BOOLEAN NOT NULL DEFAULT TRUE)")
    op.execute("CREATE TABLE IF NOT EXISTS custom_fields (id SERIAL PRIMARY KEY, key VARCHAR(100) NOT NULL UNIQUE, label VARCHAR(255) NOT NULL, field_type VARCHAR(32) NOT NULL DEFAULT 'text', value TEXT NOT NULL DEFAULT '', enabled BOOLEAN NOT NULL DEFAULT TRUE, sort_order INTEGER NOT NULL DEFAULT 0)")
    op.execute("CREATE TABLE IF NOT EXISTS menu_images (id SERIAL PRIMARY KEY, title VARCHAR(255) NOT NULL, filename VARCHAR(255) NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0, enabled BOOLEAN NOT NULL DEFAULT TRUE)")

def downgrade():
    op.execute("DROP TABLE IF EXISTS menu_images, custom_fields, bot_menu_items, app_settings")
    op.execute("DROP INDEX IF EXISTS uq_users_yandex_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS yandex_id")
