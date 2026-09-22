"""V2.1.0 production hardening: financial ledger and traceable audit records."""
from alembic import op
import sqlalchemy as sa

revision = "0033_v2_1_0_production_hardening"
down_revision = "0032_v2_0_0_product_features"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_ledger",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("operation_key", sa.String(length=160), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("balance_after", sa.Numeric(12, 2), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("operation_key", name="uq_financial_ledger_operation_key"),
    )
    op.create_index("ix_financial_ledger_user_id", "financial_ledger", ["user_id"])
    op.create_index("ix_financial_ledger_payment_id", "financial_ledger", ["payment_id"])
    op.create_index("ix_financial_ledger_created_at", "financial_ledger", ["created_at"])
    op.create_check_constraint("ck_financial_ledger_direction", "financial_ledger", "direction IN ('credit','debit')")
    op.create_check_constraint("ck_financial_ledger_amount_positive", "financial_ledger", "amount > 0")
    op.add_column("audit_logs", sa.Column("request_id", sa.String(length=64), nullable=True))
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])


def downgrade():
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_column("audit_logs", "request_id")
    op.drop_constraint("ck_financial_ledger_amount_positive", "financial_ledger", type_="check")
    op.drop_constraint("ck_financial_ledger_direction", "financial_ledger", type_="check")
    op.drop_index("ix_financial_ledger_created_at", table_name="financial_ledger")
    op.drop_index("ix_financial_ledger_payment_id", table_name="financial_ledger")
    op.drop_index("ix_financial_ledger_user_id", table_name="financial_ledger")
    op.drop_table("financial_ledger")
