"""phase-17 external_id safety"""

from alembic import op
import sqlalchemy as sa


revision = "284d96fbb2ba"
down_revision = "a8eff8f0226a"
branch_labels = None
depends_on = None


INDEX_KWARGS = {
    "postgresql_where": sa.text("external_id IS NOT NULL"),
    "sqlite_where": sa.text("external_id IS NOT NULL"),
}


def upgrade() -> None:
    # Owner profiles
    op.add_column(
        "owner_profiles",
        sa.Column("external_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ux_owner_profiles_external_id",
        "owner_profiles",
        ["external_id"],
        unique=True,
        **INDEX_KWARGS,
    )

    # Pets
    op.add_column("pets", sa.Column("external_id", sa.String(length=64), nullable=True))
    op.create_index(
        "ux_pets_external_id",
        "pets",
        ["external_id"],
        unique=True,
        **INDEX_KWARGS,
    )

    # Reservations
    op.add_column(
        "reservations",
        sa.Column("external_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ux_reservations_account_external",
        "reservations",
        ["account_id", "external_id"],
        unique=True,
        **INDEX_KWARGS,
    )

    # Invoices
    op.add_column(
        "invoices",
        sa.Column("external_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ux_invoices_account_external",
        "invoices",
        ["account_id", "external_id"],
        unique=True,
        **INDEX_KWARGS,
    )

    # Payment transactions
    op.add_column(
        "payment_transactions",
        sa.Column("external_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ux_payment_transactions_account_external",
        "payment_transactions",
        ["account_id", "external_id"],
        unique=True,
        **INDEX_KWARGS,
    )

    # Package credits
    op.add_column(
        "package_credits",
        sa.Column("external_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ux_package_credits_account_external",
        "package_credits",
        ["account_id", "external_id"],
        unique=True,
        **INDEX_KWARGS,
    )


def downgrade() -> None:
    op.drop_index("ux_package_credits_account_external", table_name="package_credits")
    op.drop_column("package_credits", "external_id")

    op.drop_index(
        "ux_payment_transactions_account_external",
        table_name="payment_transactions",
    )
    op.drop_column("payment_transactions", "external_id")

    op.drop_index("ux_invoices_account_external", table_name="invoices")
    op.drop_column("invoices", "external_id")

    op.drop_index("ux_reservations_account_external", table_name="reservations")
    op.drop_column("reservations", "external_id")

    op.drop_index("ux_pets_external_id", table_name="pets")
    op.drop_column("pets", "external_id")

    op.drop_index("ux_owner_profiles_external_id", table_name="owner_profiles")
    op.drop_column("owner_profiles", "external_id")
