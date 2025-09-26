"""Phase 11 store models and invoice credits_total."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "2d9a33a5242c"
down_revision = "0017_phase_10_report_cards_and_media"
branch_labels = None
depends_on = None


package_application_enum = sa.Enum(
    "DAYCARE", "BOARDING", "GROOMING", "CURRENCY", name="packageapplicationtype"
)
package_credit_source_enum = sa.Enum(
    "PURCHASE", "CONSUME", "ADJUST", name="packagecreditsource"
)
store_credit_source_enum = sa.Enum(
    "PURCHASE_GC", "REDEEM_GC", "REFUND", "MANUAL", "CONSUME", name="storecreditsource"
)
credit_application_type_enum = sa.Enum(
    "PACKAGE", "STORE_CREDIT", "GIFT_CERTIFICATE", name="creditapplicationtype"
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (
        package_application_enum,
        package_credit_source_enum,
        store_credit_source_enum,
        credit_application_type_enum,
    ):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "package_types",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("applies_to", package_application_enum, nullable=False),
        sa.Column(
            "credits_per_package", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
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
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "gift_certificates",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("original_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("remaining_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("purchaser_owner_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_owner_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
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
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["purchaser_owner_id"], ["owner_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["recipient_owner_id"], ["owner_profiles.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "package_credits",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("package_type_id", sa.Uuid(), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("source", package_credit_source_enum, nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=True),
        sa.Column("reservation_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["owner_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["package_type_id"], ["package_types.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["reservation_id"], ["reservations.id"], ondelete="SET NULL"
        ),
    )

    op.create_table(
        "store_credit_ledger",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("source", store_credit_source_enum, nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["owner_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "credit_applications",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("type", credit_application_type_enum, nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column("units", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("amount >= 0", name="ck_credit_app_amount_positive"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
    )

    op.add_column(
        "invoices",
        sa.Column(
            "credits_total",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("invoices", "credits_total")

    op.drop_table("credit_applications")
    op.drop_table("store_credit_ledger")
    op.drop_table("package_credits")
    op.drop_table("gift_certificates")
    op.drop_table("package_types")

    bind = op.get_bind()
    for enum in (
        credit_application_type_enum,
        store_credit_source_enum,
        package_credit_source_enum,
        package_application_enum,
    ):
        enum.drop(bind, checkfirst=True)
