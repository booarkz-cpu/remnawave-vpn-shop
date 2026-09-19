"""V24-V28 reliability, security, customer and operations"""
from alembic import op
import sqlalchemy as sa
revision="0012_v24_v28_operations"
down_revision="0011_v23_reliability"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("refund_requests",
        sa.Column("id",sa.Integer(),primary_key=True), sa.Column("payment_id",sa.Integer(),nullable=False,unique=True),
        sa.Column("user_id",sa.Integer(),nullable=False), sa.Column("amount",sa.Numeric(12,2),nullable=False),
        sa.Column("status",sa.String(32),nullable=False,server_default="requested"), sa.Column("reason",sa.Text()),
        sa.Column("provider_refund_id",sa.String(255)), sa.Column("created_at",sa.DateTime(),nullable=False), sa.Column("updated_at",sa.DateTime(),nullable=False))
    op.create_index("ix_refund_requests_user_id","refund_requests",["user_id"])
    op.create_table("support_tickets",
        sa.Column("id",sa.Integer(),primary_key=True), sa.Column("user_id",sa.Integer(),nullable=False), sa.Column("subject",sa.String(255),nullable=False),
        sa.Column("message",sa.Text(),nullable=False), sa.Column("status",sa.String(32),nullable=False,server_default="open"), sa.Column("admin_reply",sa.Text()),
        sa.Column("created_at",sa.DateTime(),nullable=False), sa.Column("updated_at",sa.DateTime(),nullable=False))
    op.create_index("ix_support_tickets_user_id","support_tickets",["user_id"])
    op.create_table("withdrawal_requests",
        sa.Column("id",sa.Integer(),primary_key=True), sa.Column("user_id",sa.Integer(),nullable=False), sa.Column("amount",sa.Numeric(12,2),nullable=False),
        sa.Column("destination",sa.String(255),nullable=False), sa.Column("status",sa.String(32),nullable=False,server_default="requested"), sa.Column("admin_note",sa.Text()),
        sa.Column("created_at",sa.DateTime(),nullable=False), sa.Column("updated_at",sa.DateTime(),nullable=False))
    op.create_index("ix_withdrawal_requests_user_id","withdrawal_requests",["user_id"])
    op.create_table("worker_states",
        sa.Column("id",sa.Integer(),primary_key=True), sa.Column("worker_id",sa.String(128),nullable=False,unique=True), sa.Column("role",sa.String(64),nullable=False),
        sa.Column("status",sa.String(32),nullable=False,server_default="online"), sa.Column("current_job",sa.String(255)), sa.Column("last_seen_at",sa.DateTime(),nullable=False))
    op.create_index("ix_worker_states_worker_id","worker_states",["worker_id"],unique=True)
    op.create_table("release_records",
        sa.Column("id",sa.Integer(),primary_key=True), sa.Column("version",sa.String(64),nullable=False), sa.Column("status",sa.String(32),nullable=False,server_default="created"),
        sa.Column("rollback_archive",sa.Text()), sa.Column("details",sa.Text()), sa.Column("created_at",sa.DateTime(),nullable=False), sa.Column("completed_at",sa.DateTime()))
    op.create_table("security_incidents",
        sa.Column("id",sa.Integer(),primary_key=True), sa.Column("kind",sa.String(64),nullable=False), sa.Column("severity",sa.String(16),nullable=False,server_default="medium"),
        sa.Column("status",sa.String(32),nullable=False,server_default="open"), sa.Column("details",sa.Text()), sa.Column("created_at",sa.DateTime(),nullable=False), sa.Column("resolved_at",sa.DateTime()))

def downgrade():
    op.drop_table("security_incidents"); op.drop_table("release_records"); op.drop_index("ix_worker_states_worker_id",table_name="worker_states"); op.drop_table("worker_states")
    op.drop_index("ix_withdrawal_requests_user_id",table_name="withdrawal_requests"); op.drop_table("withdrawal_requests")
    op.drop_index("ix_support_tickets_user_id",table_name="support_tickets"); op.drop_table("support_tickets")
    op.drop_index("ix_refund_requests_user_id",table_name="refund_requests"); op.drop_table("refund_requests")
