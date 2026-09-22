"""V2.6.0 platform: abuse, node agent, API keys, webhooks, plugins."""
from alembic import op
import sqlalchemy as sa

revision = "0038_v2_6_0_platform"
down_revision = "0037_v2_5_0_tariff_constructor"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("restricted_at", sa.DateTime(), nullable=True))
    op.create_table(
        "connection_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("remnawave_uuid", sa.String(64), nullable=True),
        sa.Column("ip", sa.String(64), nullable=False),
        sa.Column("prefix", sa.String(80), nullable=False),
        sa.Column("asn", sa.String(32), nullable=True),
        sa.Column("asn_org", sa.String(255), nullable=True),
        sa.Column("country", sa.String(16), nullable=True),
        sa.Column("lat", sa.Numeric(8, 5), nullable=True),
        sa.Column("lon", sa.Numeric(8, 5), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("hwid", sa.String(128), nullable=True),
        sa.Column("mobile", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("torrent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("seen_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_connection_observations_user_id", "connection_observations", ["user_id"])
    op.create_index("ix_connection_observations_remnawave_uuid", "connection_observations", ["remnawave_uuid"])
    op.create_index("ix_connection_observations_hwid", "connection_observations", ["hwid"])
    op.create_table(
        "abuse_violations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommendation", sa.String(32), nullable=False, server_default="observe"),
        sa.Column("analyzers", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_abuse_violations_user_id", "abuse_violations", ["user_id"])
    op.create_index("ix_abuse_violations_status", "abuse_violations", ["status"])
    op.create_table(
        "device_blacklist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hwid", sa.String(128), nullable=False, unique=True),
        sa.Column("action", sa.String(16), nullable=False, server_default="alert"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "node_agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cpu", sa.String(32), nullable=True),
        sa.Column("mem", sa.String(32), nullable=True),
        sa.Column("disk", sa.String(32), nullable=True),
        sa.Column("xray_ok", sa.Boolean(), nullable=True),
        sa.Column("version", sa.String(32), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "agent_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_agent_actions_agent_id", "agent_actions", ["agent_id"])
    op.create_index("ix_agent_actions_status", "agent_actions", ["status"])
    op.create_table(
        "shop_api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("prefix", sa.String(24), nullable=False),
        sa.Column("secret_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("scopes", sa.String(255), nullable=False, server_default="read"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "outbound_webhooks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret_encrypted", sa.Text(), nullable=False),
        sa.Column("events", sa.String(255), nullable=False, server_default="abuse.scored"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_status", sa.String(32), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "platform_plugins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
    )
    op.execute(
        """
        INSERT INTO platform_plugins (key, enabled, description) VALUES
        ('abuse', true, 'Скоринг разделения подписки'),
        ('agent', true, 'Агент узла: метрики и наблюдения'),
        ('webhooks', true, 'Исходящие webhook с подписью'),
        ('mail', true, 'Исходящая почта SMTP и подсказка DKIM'),
        ('metrics', true, 'Дополнительные метрики Prometheus'),
        ('torrents', true, 'Флаг торрента от агента')
        """
    )


def downgrade():
    op.drop_table("platform_plugins")
    op.drop_table("outbound_webhooks")
    op.drop_table("shop_api_keys")
    op.drop_index("ix_agent_actions_status", table_name="agent_actions")
    op.drop_index("ix_agent_actions_agent_id", table_name="agent_actions")
    op.drop_table("agent_actions")
    op.drop_table("node_agents")
    op.drop_table("device_blacklist")
    op.drop_index("ix_abuse_violations_status", table_name="abuse_violations")
    op.drop_index("ix_abuse_violations_user_id", table_name="abuse_violations")
    op.drop_table("abuse_violations")
    op.drop_index("ix_connection_observations_hwid", table_name="connection_observations")
    op.drop_index("ix_connection_observations_remnawave_uuid", table_name="connection_observations")
    op.drop_index("ix_connection_observations_user_id", table_name="connection_observations")
    op.drop_table("connection_observations")
    op.drop_column("users", "restricted_at")
