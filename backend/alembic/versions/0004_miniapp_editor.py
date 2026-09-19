"""mini app visual editor settings"""
from alembic import op

revision="0004_miniapp_editor"
down_revision="0003_marketing"
branch_labels=None
depends_on=None

def upgrade():
    op.execute("INSERT INTO app_settings(key,value) VALUES ('miniapp_title','') ON CONFLICT (key) DO NOTHING")
    op.execute("INSERT INTO app_settings(key,value) VALUES ('miniapp_subtitle','') ON CONFLICT (key) DO NOTHING")
    op.execute("INSERT INTO app_settings(key,value) VALUES ('miniapp_background_color','#f5f7fb') ON CONFLICT (key) DO NOTHING")
    op.execute("INSERT INTO app_settings(key,value) VALUES ('miniapp_background_image','') ON CONFLICT (key) DO NOTHING")
    op.execute("INSERT INTO app_settings(key,value) VALUES ('miniapp_instructions','') ON CONFLICT (key) DO NOTHING")
    op.execute("INSERT INTO app_settings(key,value) VALUES ('miniapp_buttons','[]') ON CONFLICT (key) DO NOTHING")

def downgrade():
    op.execute("DELETE FROM app_settings WHERE key IN ('miniapp_title','miniapp_subtitle','miniapp_background_color','miniapp_background_image','miniapp_instructions','miniapp_buttons')")
