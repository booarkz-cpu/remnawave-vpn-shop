"""V1.0.0 release: database-enforced payment idempotency.

Revision ID: 0031_v1_0_0_idempotency_integrity
Revises: 0030_v44_5_16_privacy_and_refund_integrity
"""
from alembic import op
import sqlalchemy as sa

revision = "0031_v1_0_0_idempotency_integrity"
down_revision = "0030_v44_5_16_privacy_and_refund_integrity"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    duplicates = bind.execute(sa.text("""
        SELECT user_id, idempotency_key, COUNT(*) AS duplicate_count
        FROM payments
        WHERE idempotency_key IS NOT NULL
        GROUP BY user_id, idempotency_key
        HAVING COUNT(*) > 1
        ORDER BY user_id, idempotency_key
        LIMIT 20
    """)).fetchall()
    if duplicates:
        rendered = "; ".join(
            f"user_id={row.user_id}, idempotency_key={row.idempotency_key!r}, count={row.duplicate_count}"
            for row in duplicates
        )
        raise RuntimeError(
            "V1.0.0 migration refused: duplicate payment idempotency keys exist. "
            f"Reconcile these rows before migration: {rendered}"
        )
    op.create_unique_constraint(
        "uq_payments_user_idempotency_key",
        "payments",
        ["user_id", "idempotency_key"],
    )


def downgrade():
    op.drop_constraint("uq_payments_user_idempotency_key", "payments", type_="unique")
