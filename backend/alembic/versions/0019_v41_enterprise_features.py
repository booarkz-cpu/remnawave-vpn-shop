"""V41 enterprise operations, payment resilience, incidents, backups and passkey storage."""
from alembic import op
import sqlalchemy as sa

revision = "0019_v41_enterprise_features"
down_revision = "0018_v40_security_gate"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("feature_flags",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_index("ix_feature_flags_key", "feature_flags", ["key"], unique=True)
    op.create_table("payment_provider_health",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("provider", sa.String(32), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_latency_ms", sa.Integer()), sa.Column("last_error", sa.Text()), sa.Column("circuit_open_until", sa.DateTime()), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_index("ix_payment_provider_health_provider", "payment_provider_health", ["provider"], unique=True)
    op.create_table("security_incident_events",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("severity", sa.String(16), nullable=False), sa.Column("category", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False), sa.Column("details", sa.Text()), sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("resolved_at", sa.DateTime()))
    op.create_table("backup_verifications",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("backup_id", sa.Integer(), nullable=False), sa.Column("status", sa.String(32), nullable=False),
        sa.Column("checksum_ok", sa.Boolean()), sa.Column("archive_safe", sa.Boolean()), sa.Column("restore_tested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("finished_at", sa.DateTime()))
    op.create_index("ix_backup_verifications_backup_id", "backup_verifications", ["backup_id"])
    op.create_table("webauthn_credentials",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("admin_id", sa.Integer(), nullable=False), sa.Column("credential_id", sa.String(1024), nullable=False, unique=True),
        sa.Column("public_key", sa.Text(), nullable=False), sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("transports", sa.String(255)),
        sa.Column("name", sa.String(100), nullable=False, server_default="Passkey"), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("last_used_at", sa.DateTime()))
    op.create_index("ix_webauthn_credentials_admin_id", "webauthn_credentials", ["admin_id"])
    op.create_index("ix_webauthn_credentials_credential_id", "webauthn_credentials", ["credential_id"], unique=True)


def downgrade():
    op.drop_table("webauthn_credentials")
    op.drop_table("backup_verifications")
    op.drop_table("security_incident_events")
    op.drop_table("payment_provider_health")
    op.drop_table("feature_flags")
