"""Initial core schema.

Revision ID: 0001
Revises:
Create Date: 2025-09-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False, unique=True),
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

    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("address_line1", sa.String(length=255)),
        sa.Column("address_line2", sa.String(length=255)),
        sa.Column("city", sa.String(length=120)),
        sa.Column("state", sa.String(length=120)),
        sa.Column("postal_code", sa.String(length=32)),
        sa.Column("phone_number", sa.String(length=32)),
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

    user_role_enum = sa.Enum(
        "superadmin",
        "admin",
        "manager",
        "staff",
        "pet_parent",
        name="userrole",
    )
    user_status_enum = sa.Enum(
        "invited",
        "active",
        "suspended",
        name="userstatus",
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("phone_number", sa.String(length=32)),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("status", user_status_enum, nullable=False, server_default="invited"),
        sa.Column(
            "is_primary_contact",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
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

    op.create_index("ix_users_account_id", "users", ["account_id"])
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "owner_profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("preferred_contact_method", sa.String(length=32)),
        sa.Column("notes", sa.String(length=1024)),
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

    pet_type_enum = sa.Enum("dog", "cat", "other", name="pettype")

    op.create_table(
        "pets",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("owner_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "home_location_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="SET NULL"),
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("pet_type", pet_type_enum, nullable=False),
        sa.Column("breed", sa.String(length=120)),
        sa.Column("color", sa.String(length=120)),
        sa.Column("date_of_birth", sa.Date()),
        sa.Column("notes", sa.String(length=1024)),
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

    reservation_type_enum = sa.Enum(
        "boarding",
        "daycare",
        "grooming",
        "training",
        "other",
        name="reservationtype",
    )
    reservation_status_enum = sa.Enum(
        "requested",
        "confirmed",
        "checked_in",
        "checked_out",
        "canceled",
        name="reservationstatus",
    )

    op.create_table(
        "reservations",
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
        sa.Column("reservation_type", reservation_type_enum, nullable=False),
        sa.Column(
            "status",
            reservation_status_enum,
            nullable=False,
            server_default="requested",
        ),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("base_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("notes", sa.String(length=1024)),
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

    op.create_index("ix_reservations_account_id", "reservations", ["account_id"])
    op.create_index("ix_reservations_location_id", "reservations", ["location_id"])
    op.create_index("ix_reservations_pet_id", "reservations", ["pet_id"])
    op.create_index("ix_reservations_status", "reservations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_reservations_status", table_name="reservations")
    op.drop_index("ix_reservations_pet_id", table_name="reservations")
    op.drop_index("ix_reservations_location_id", table_name="reservations")
    op.drop_index("ix_reservations_account_id", table_name="reservations")
    op.drop_table("reservations")
    sa.Enum(name="reservationstatus").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="reservationtype").drop(op.get_bind(), checkfirst=False)

    op.drop_table("pets")
    sa.Enum(name="pettype").drop(op.get_bind(), checkfirst=False)

    op.drop_table("owner_profiles")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_account_id", table_name="users")
    op.drop_table("users")
    sa.Enum(name="userstatus").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=False)

    op.drop_table("locations")
    op.drop_table("accounts")
