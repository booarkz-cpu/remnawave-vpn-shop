"""V30 final production hardening state constraints."""
from alembic import op
import sqlalchemy as sa
revision="0014_v30_final_hardening"
down_revision="0013_v29_final_hardening"
branch_labels=None
depends_on=None

def upgrade():
    op.create_check_constraint("ck_refund_status_v30", "refund_requests", "status IN ('requested','review','approved','processing','refunded','refunded_pending_revoke','failed','rejected')")
    op.create_check_constraint("ck_withdrawal_status_v30", "withdrawal_requests", "status IN ('requested','approved','processing','paid','rejected','cancelled')")

def downgrade():
    op.drop_constraint("ck_withdrawal_status_v30", "withdrawal_requests", type_="check")
    op.drop_constraint("ck_refund_status_v30", "refund_requests", type_="check")
