"""V16-V19 reliability, sessions, referrals, fulfillment and backups"""
from alembic import op
import sqlalchemy as sa
revision="0008_v16_v19"
down_revision="0007_v15_production"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("users", sa.Column("referral_code", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("referred_by_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("auto_renew_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("referral_balance", sa.Numeric(12,2), nullable=False, server_default="0"))
    op.execute("UPDATE users SET referral_code='U'||id WHERE referral_code IS NULL")
    op.alter_column("users", "referral_code", nullable=False)
    op.create_unique_constraint("uq_users_referral_code", "users", ["referral_code"])
    op.create_index("ix_users_referral_code", "users", ["referral_code"])
    for name, col in [
        ("fulfillment_status", sa.String(32)),
        ("fulfillment_attempts",sa.Integer()),
        ("fulfillment_error",sa.Text()),
        ("next_retry_at",sa.DateTime()),
        ("idempotency_key",sa.String(128))
    ]:
        op.add_column("payments", sa.Column(name, col, nullable=True))
    op.execute("UPDATE payments SET fulfillment_status=CASE WHEN status='paid' THEN 'completed' ELSE 'pending' END WHERE fulfillment_status IS NULL")
    op.execute("UPDATE payments SET fulfillment_attempts=0 WHERE fulfillment_attempts IS NULL")
    op.alter_column("payments","fulfillment_status",nullable=False,server_default="pending")
    op.alter_column("payments","fulfillment_attempts",nullable=False,server_default="0")
    op.create_index("ix_payments_next_retry_at","payments",["next_retry_at"])
    op.create_index("ix_payments_fulfillment_status","payments",["fulfillment_status"])
    op.create_table("admin_sessions", sa.Column("id",sa.Integer,primary_key=True), sa.Column("admin_id",sa.Integer,nullable=False), sa.Column("jti_hash",sa.String(64),nullable=False), sa.Column("ip",sa.String(64)), sa.Column("user_agent",sa.String(512)), sa.Column("created_at",sa.DateTime,server_default=sa.func.now(),nullable=False), sa.Column("last_seen_at",sa.DateTime,server_default=sa.func.now(),nullable=False), sa.Column("expires_at",sa.DateTime,nullable=False), sa.Column("revoked_at",sa.DateTime), sa.UniqueConstraint("jti_hash"))
    op.create_index("ix_admin_sessions_admin_id","admin_sessions",["admin_id"])
    op.create_table("promo_redemptions", sa.Column("id",sa.Integer,primary_key=True), sa.Column("promo_code_id",sa.Integer,nullable=False), sa.Column("user_id",sa.Integer,nullable=False), sa.Column("payment_id",sa.Integer,nullable=False,unique=True), sa.Column("created_at",sa.DateTime,server_default=sa.func.now(),nullable=False))
    op.create_index("ix_promo_redemptions_promo_code_id","promo_redemptions",["promo_code_id"])
    op.create_table("referral_rewards", sa.Column("id",sa.Integer,primary_key=True), sa.Column("referrer_id",sa.Integer,nullable=False), sa.Column("referred_user_id",sa.Integer,nullable=False), sa.Column("payment_id",sa.Integer,nullable=False,unique=True), sa.Column("amount",sa.Numeric(12,2),nullable=False), sa.Column("status",sa.String(32),server_default="credited",nullable=False), sa.Column("created_at",sa.DateTime,server_default=sa.func.now(),nullable=False))
    op.create_index("ix_referral_rewards_referrer_id","referral_rewards",["referrer_id"])

def downgrade():
    op.drop_table("referral_rewards"); op.drop_table("promo_redemptions"); op.drop_table("admin_sessions")
    for col in ["idempotency_key","next_retry_at","fulfillment_error","fulfillment_attempts","fulfillment_status"]: op.drop_column("payments",col)
    op.drop_constraint("uq_users_referral_code","users",type_="unique"); op.drop_column("users","referral_balance"); op.drop_column("users","auto_renew_enabled"); op.drop_column("users","referred_by_id"); op.drop_column("users","referral_code")
