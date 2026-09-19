"""V32 operations, fraud, payouts and job queue."""
from alembic import op
import sqlalchemy as sa
revision="0015_v32_operations"
down_revision="0014_v30_final_hardening"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("jobs",
        sa.Column("id",sa.Integer(),primary_key=True), sa.Column("job_key",sa.String(128),nullable=False,unique=True),
        sa.Column("kind",sa.String(64),nullable=False), sa.Column("status",sa.String(32),nullable=False,server_default="queued"),
        sa.Column("attempts",sa.Integer(),nullable=False,server_default="0"), sa.Column("max_attempts",sa.Integer(),nullable=False,server_default="8"),
        sa.Column("next_retry_at",sa.DateTime()), sa.Column("locked_at",sa.DateTime()), sa.Column("worker_id",sa.String(128)),
        sa.Column("error",sa.Text()), sa.Column("payload",sa.JSON()), sa.Column("created_at",sa.DateTime(),nullable=False), sa.Column("completed_at",sa.DateTime()))
    op.create_index("ix_jobs_kind","jobs",["kind"]); op.create_index("ix_jobs_status","jobs",["status"]); op.create_index("ix_jobs_worker_id","jobs",["worker_id"])
    op.create_table("fraud_signals",
        sa.Column("id",sa.Integer(),primary_key=True), sa.Column("user_id",sa.Integer()), sa.Column("ip",sa.String(64)), sa.Column("fingerprint",sa.String(128)),
        sa.Column("kind",sa.String(64),nullable=False), sa.Column("score",sa.Integer(),nullable=False,server_default="0"), sa.Column("status",sa.String(32),nullable=False,server_default="open"),
        sa.Column("details",sa.Text()), sa.Column("created_at",sa.DateTime(),nullable=False), sa.Column("resolved_at",sa.DateTime()))
    for col in ("user_id","ip","fingerprint","kind","status"): op.create_index(f"ix_fraud_signals_{col}","fraud_signals",[col])
    op.create_table("payout_transactions",
        sa.Column("id",sa.Integer(),primary_key=True), sa.Column("withdrawal_id",sa.Integer(),nullable=False,unique=True), sa.Column("provider",sa.String(32),nullable=False,server_default="manual"),
        sa.Column("external_id",sa.String(255),unique=True), sa.Column("amount",sa.Numeric(12,2),nullable=False), sa.Column("status",sa.String(32),nullable=False,server_default="processing"),
        sa.Column("attempts",sa.Integer(),nullable=False,server_default="0"), sa.Column("last_error",sa.Text()), sa.Column("created_at",sa.DateTime(),nullable=False),
        sa.Column("updated_at",sa.DateTime(),nullable=False), sa.Column("paid_at",sa.DateTime()))
    op.create_check_constraint("ck_payout_status_v32","payout_transactions","status IN ('processing','paid','failed','rejected')")

def downgrade():
    op.drop_constraint("ck_payout_status_v32","payout_transactions",type_="check"); op.drop_table("payout_transactions"); op.drop_table("fraud_signals"); op.drop_table("jobs")
