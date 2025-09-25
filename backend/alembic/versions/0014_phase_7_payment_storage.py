"""Phase 7 payment storage and idempotency tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    payment_status_enum = sa.Enum(
        "requires_payment_method",
        "requires_confirmation",
        "processing",
        "succeeded",
        "canceled",
        "failed",
        "refunded",
        "partial_refund",
        name="paymenttransactionstatus",
    )
    payment_status_enum.create(op.get_bind(), checkfirst=True)

    jsonb_type = postgresql.JSONB(astext_type=sa.Text()).with_variant(
        sa.JSON(), "sqlite"
    )

    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("owner_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "provider", sa.String(length=32), nullable=False, server_default="stripe"
        ),
        sa.Column("provider_payment_intent_id", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "currency", sa.String(length=12), nullable=False, server_default="usd"
        ),
        sa.Column("status", payment_status_enum, nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "provider_payment_intent_id",
            name="uq_payment_transactions_payment_intent",
        ),
    )

    op.create_table(
        "payment_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("raw", jsonb_type, nullable=False),
        sa.UniqueConstraint(
            "provider_event_id", name="uq_payment_events_provider_event"
        ),
    )


def downgrade() -> None:
    op.drop_table("payment_events")
    op.drop_table("payment_transactions")
    sa.Enum(name="paymenttransactionstatus").drop(op.get_bind(), checkfirst=True)
