"""V2.4.0 cabinet: email/VK auth, cabinet menu, sandbox payments."""
from alembic import op
import sqlalchemy as sa

revision = "0036_v2_4_0_cabinet"
down_revision = "0035_v2_3_0_wallet_gifts"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("vk_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("email", sa.String(320), nullable=True))
    op.add_column("users", sa.Column("email_password_hash", sa.String(512), nullable=True))
    op.create_index("ix_users_vk_id", "users", ["vk_id"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "cabinet_menu_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="custom"),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("slug", name="uq_cabinet_menu_items_slug"),
    )
    op.create_index("ix_cabinet_menu_items_slug", "cabinet_menu_items", ["slug"])
    # Seed default tabs
    op.execute(
        """
        INSERT INTO cabinet_menu_items (title, slug, kind, body, sort_order, enabled) VALUES
        ('Обзор', 'overview', 'overview', '', 10, true),
        ('Тарифы', 'plans', 'plans', '', 20, true),
        ('Пробный период', 'trial', 'trial', '', 30, true),
        ('Подключение', 'connection', 'connection', '', 40, true),
        ('Поддержка', 'support', 'support', '', 50, true)
        """
    )


def downgrade():
    op.drop_table("cabinet_menu_items")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_vk_id", table_name="users")
    op.drop_column("users", "email_password_hash")
    op.drop_column("users", "email")
    op.drop_column("users", "vk_id")
