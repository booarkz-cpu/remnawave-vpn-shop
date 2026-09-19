"""V44.5.10: durable payment intents and webhook event conflict integrity."""
from alembic import op
import sqlalchemy as sa

revision = "0027_v44_5_10_financial_integrity"
down_revision = "0026_v44_5_9_retry_hardening"
branch_labels = None
depends_on = None

def upgrade():
    # Payment intents must exist before an external charge. NULL is used until
    # the provider returns its payment id; the existing unique index remains
    # valid because PostgreSQL permits multiple NULLs in a unique index.
    op.alter_column("payments", "provider_payment_id", existing_type=sa.String(255), nullable=True)
    # The original schema made event_id globally unique, while the application
    # attempted ON CONFLICT(provider,event_id). Align the database invariant
    # with the provider-scoped event identity used by all webhook handlers.
    op.drop_constraint("uq_payment_provider_events_event_id", "payment_provider_events", type_="unique")
    op.create_unique_constraint("uq_payment_provider_events_provider_event", "payment_provider_events", ["provider", "event_id"])

def downgrade():
    op.drop_constraint("uq_payment_provider_events_provider_event", "payment_provider_events", type_="unique")
    op.create_unique_constraint("uq_payment_provider_events_event_id", "payment_provider_events", ["event_id"])
    op.alter_column("payments", "provider_payment_id", existing_type=sa.String(255), nullable=False)
