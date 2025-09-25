"""Add service catalog, packages, waitlists, documents, and location hours."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    service_kind_enum = sa.Enum("service", "retail", name="servicecatalogkind")
    service_kind_enum.create(op.get_bind(), checkfirst=True)

    waitlist_status_enum = sa.Enum(
        "pending", "offered", "confirmed", "canceled", name="waitliststatus"
    )
    waitlist_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "service_catalog_items",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("kind", service_kind_enum, nullable=False),
        sa.Column("reservation_type", sa.Enum(name="reservationtype"), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sku", sa.String(length=64), nullable=True, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_service_catalog_items_account_id",
        "service_catalog_items",
        ["account_id"],
    )

    op.create_table(
        "service_packages",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("reservation_type", sa.Enum(name="reservationtype"), nullable=False),
        sa.Column("credit_quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_service_packages_account_id",
        "service_packages",
        ["account_id"],
    )

    op.create_table(
        "waitlist_entries",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "location_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pet_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("pets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reservation_type", sa.Enum(name="reservationtype"), nullable=False),
        sa.Column("desired_date", sa.Date(), nullable=False),
        sa.Column(
            "status", waitlist_status_enum, nullable=False, server_default="pending"
        ),
        sa.Column("notes", sa.String(length=1024), nullable=True),
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_waitlist_entries_account_id",
        "waitlist_entries",
        ["account_id"],
    )

    op.create_table(
        "location_hours",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "location_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("open_time", sa.Time(), nullable=True),
        sa.Column("close_time", sa.Time(), nullable=True),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_location_hours_location_id",
        "location_hours",
        ["location_id"],
    )

    op.create_table(
        "location_closures",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "location_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_location_closures_location_id",
        "location_closures",
        ["location_id"],
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("owner_profiles.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "pet_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("pets.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "uploaded_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("notes", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_documents_account_id",
        "documents",
        ["account_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_account_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_location_closures_location_id", table_name="location_closures")
    op.drop_table("location_closures")

    op.drop_index("ix_location_hours_location_id", table_name="location_hours")
    op.drop_table("location_hours")

    op.drop_index("ix_waitlist_entries_account_id", table_name="waitlist_entries")
    op.drop_table("waitlist_entries")

    op.drop_index("ix_service_packages_account_id", table_name="service_packages")
    op.drop_table("service_packages")

    op.drop_index(
        "ix_service_catalog_items_account_id", table_name="service_catalog_items"
    )
    op.drop_table("service_catalog_items")

    sa.Enum(name="waitliststatus").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="servicecatalogkind").drop(op.get_bind(), checkfirst=False)
