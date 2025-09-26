"""Add deposits table and invoice total columns."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    deposit_status = sa.Enum(
        "held",
        "consumed",
        "refunded",
        "forfeited",
        name="depositstatus",
    )
    deposit_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "deposits",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reservation_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("reservations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("owner_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", deposit_status, nullable=False),
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
    )

    op.add_column(
        "invoices",
        sa.Column(
            "subtotal",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "discount_total",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "tax_total",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
    )

    op.execute("UPDATE invoices SET subtotal = total_amount WHERE subtotal = 0")


def downgrade() -> None:
    op.drop_column("invoices", "tax_total")
    op.drop_column("invoices", "discount_total")
    op.drop_column("invoices", "subtotal")

    op.drop_table("deposits")

    deposit_status = sa.Enum(
        "held",
        "consumed",
        "refunded",
        "forfeited",
        name="depositstatus",
    )
    deposit_status.drop(op.get_bind(), checkfirst=True)
