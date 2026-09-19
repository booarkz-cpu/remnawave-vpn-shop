"""V20-V21 hardening, reconciliation, referral ledger and auto-renew tokens"""
from alembic import op
import sqlalchemy as sa
revision = "0009_v20_v21"
down_revision = "0008_v16_v19"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("payment_provider_events",
        sa.Column("id",sa.Integer,primary_key=True),
        sa.Column("provider",sa.String(32),nullable=False),
        sa.Column("event_id",sa.String(255),nullable=False),
        sa.Column("payment_id",sa.Integer),
        sa.Column("received_at",sa.DateTime(),server_default=sa.func.now(),nullable=False),
        sa.UniqueConstraint("event_id",name="uq_payment_provider_events_event_id"))
    op.create_index("ix_payment_provider_events_event_id","payment_provider_events",["event_id"])
    op.create_index("ix_payment_provider_events_payment_id","payment_provider_events",["payment_id"])
    op.create_table("referral_ledger",
        sa.Column("id",sa.Integer,primary_key=True), sa.Column("user_id",sa.Integer,nullable=False),
        sa.Column("source_user_id",sa.Integer), sa.Column("payment_id",sa.Integer,unique=True),
        sa.Column("amount",sa.Numeric(12,2),nullable=False), sa.Column("kind",sa.String(32),server_default="reward",nullable=False),
        sa.Column("created_at",sa.DateTime(),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_referral_ledger_user_id","referral_ledger",["user_id"])
    op.create_index("ix_referral_ledger_source_user_id","referral_ledger",["source_user_id"])
    op.create_index("ix_referral_ledger_payment_id","referral_ledger",["payment_id"])
    op.create_table("auto_renew_methods",
        sa.Column("id",sa.Integer,primary_key=True), sa.Column("user_id",sa.Integer,unique=True,nullable=False),
        sa.Column("provider",sa.String(32),nullable=False), sa.Column("external_token_encrypted",sa.Text,nullable=False),
        sa.Column("enabled",sa.Boolean,server_default=sa.true(),nullable=False), sa.Column("last_attempt_at",sa.DateTime),
        sa.Column("last_success_at",sa.DateTime), sa.Column("last_error",sa.Text), sa.Column("created_at",sa.DateTime(),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_auto_renew_methods_user_id","auto_renew_methods",["user_id"])

def downgrade():
    op.drop_table("auto_renew_methods"); op.drop_table("referral_ledger"); op.drop_table("payment_provider_events")
