"""V2.5.0 tariff constructor: devices, traffic and duration options."""
from alembic import op
import sqlalchemy as sa

revision = "0037_v2_5_0_tariff_constructor"
down_revision = "0036_v2_4_0_cabinet"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tariff_constructors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("remnawave_profile_id", sa.String(255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_tariff_constructors_plan_id", "tariff_constructors", ["plan_id"])
    op.create_table(
        "tariff_constructor_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("constructor_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_tariff_constructor_options_constructor_id", "tariff_constructor_options", ["constructor_id"])
    op.execute(
        """
        INSERT INTO cabinet_menu_items (title, slug, kind, body, sort_order, enabled)
        SELECT 'Серверы', 'servers', 'servers', '', 45, true
        WHERE NOT EXISTS (SELECT 1 FROM cabinet_menu_items WHERE slug = 'servers')
        """
    )


def downgrade():
    op.execute("DELETE FROM cabinet_menu_items WHERE slug = 'servers' AND kind = 'servers'")
    op.drop_index("ix_tariff_constructor_options_constructor_id", table_name="tariff_constructor_options")
    op.drop_table("tariff_constructor_options")
    op.drop_index("ix_tariff_constructors_plan_id", table_name="tariff_constructors")
    op.drop_table("tariff_constructors")
