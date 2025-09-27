"""Phase 14 waitlist and confirmations."""

from __future__ import annotations

from typing import cast

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.sqltypes import Enum as SqlEnumType

# revision identifiers, used by Alembic.
revision = "38e1f2fc686b"
down_revision = "f02bc10fe274"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            "ALTER TYPE reservationstatus ADD VALUE IF NOT EXISTS 'pending_confirmation'"
        )
        op.execute(
            "ALTER TYPE reservationstatus ADD VALUE IF NOT EXISTS 'offered_from_waitlist'"
        )
        op.execute("DROP TABLE IF EXISTS waitlist_entries CASCADE")
        op.execute("DROP TYPE IF EXISTS waitliststatus CASCADE")
        op.execute("DROP TYPE IF EXISTS waitlistservicetype CASCADE")
        op.execute("DROP TYPE IF EXISTS confirmationmethod CASCADE")
        bind.execute(
            sa.text(
                "CREATE TYPE waitliststatus AS ENUM ('open','offered','converted','canceled','expired')"
            )
        )
        bind.execute(
            sa.text(
                "CREATE TYPE waitlistservicetype AS ENUM ('boarding','daycare','grooming')"
            )
        )
        bind.execute(sa.text("CREATE TYPE confirmationmethod AS ENUM ('email','sms')"))

        waitlist_status_enum = cast(
            SqlEnumType,
            postgresql.ENUM(
                "open",
                "offered",
                "converted",
                "canceled",
                "expired",
                name="waitliststatus",
                create_type=False,
            ),
        )
        waitlist_service_enum = cast(
            SqlEnumType,
            postgresql.ENUM(
                "boarding",
                "daycare",
                "grooming",
                name="waitlistservicetype",
                create_type=False,
            ),
        )
        confirmation_method_enum = cast(
            SqlEnumType,
            postgresql.ENUM(
                "email",
                "sms",
                name="confirmationmethod",
                create_type=False,
            ),
        )
    else:
        op.execute("DROP TABLE IF EXISTS waitlist_entries")
        waitlist_status_enum = cast(
            SqlEnumType,
            sa.Enum(
                "open",
                "offered",
                "converted",
                "canceled",
                "expired",
                name="waitliststatus",
            ),
        )
        waitlist_service_enum = cast(
            SqlEnumType,
            sa.Enum(
                "boarding",
                "daycare",
                "grooming",
                name="waitlistservicetype",
            ),
        )
        confirmation_method_enum = cast(
            SqlEnumType,
            sa.Enum(
                "email",
                "sms",
                name="confirmationmethod",
            ),
        )

    json_type = (
        postgresql.JSONB(astext_type=sa.Text())
        if dialect == "postgresql"
        else sa.JSON()
    )

    op.create_table(
        "lodging_types",
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
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
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
    op.create_index("ix_lodging_location", "lodging_types", ["location_id"])

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
            "owner_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("owner_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reservation_request_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("reservations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("service_type", waitlist_service_enum, nullable=False),
        sa.Column(
            "lodging_type_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("lodging_types.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("pets_json", json_type, nullable=False),
        sa.Column("notes", sa.String(length=1024), nullable=True),
        sa.Column(
            "status", waitlist_status_enum, nullable=False, server_default="open"
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "converted_reservation_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("reservations.id", ondelete="SET NULL"),
            nullable=True,
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
        sa.CheckConstraint("start_date <= end_date", name="ck_waitlist_date_order"),
    )

    op.create_index("ix_waitlist_account", "waitlist_entries", ["account_id"])
    op.create_index("ix_waitlist_location", "waitlist_entries", ["location_id"])
    op.create_index("ix_waitlist_start_date", "waitlist_entries", ["start_date"])
    op.create_index("ix_waitlist_status", "waitlist_entries", ["status"])
    op.create_index(
        "ix_waitlist_open_status",
        "waitlist_entries",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'open'"),
        sqlite_where=sa.text("status = 'open'"),
    )
    op.create_index(
        "ux_waitlist_owner_service_span_open",
        "waitlist_entries",
        ["owner_id", "service_type", "start_date", "end_date"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
        sqlite_where=sa.text("status = 'open'"),
    )

    op.create_table(
        "confirmation_tokens",
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
        sa.Column("token", sa.String(length=64), nullable=False, unique=True),
        sa.Column("method", confirmation_method_enum, nullable=False),
        sa.Column("sent_to", sa.String(length=320), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
    op.create_index("ix_confirmation_account", "confirmation_tokens", ["account_id"])
    op.create_index(
        "ix_confirmation_reservation", "confirmation_tokens", ["reservation_id"]
    )
    op.create_index("ix_confirmation_expires", "confirmation_tokens", ["expires_at"])


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.drop_index("ix_confirmation_expires", table_name="confirmation_tokens")
    op.drop_index("ix_confirmation_reservation", table_name="confirmation_tokens")
    op.drop_index("ix_confirmation_account", table_name="confirmation_tokens")
    op.drop_table("confirmation_tokens")

    op.drop_index("ux_waitlist_owner_service_span_open", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_open_status", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_status", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_start_date", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_location", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_account", table_name="waitlist_entries")
    op.drop_table("waitlist_entries")

    op.drop_index("ix_lodging_location", table_name="lodging_types")
    op.drop_table("lodging_types")

    if dialect == "postgresql":
        confirmation_method_enum = cast(SqlEnumType, sa.Enum(name="confirmationmethod"))
        waitlist_service_enum = cast(SqlEnumType, sa.Enum(name="waitlistservicetype"))
        waitlist_status_enum = cast(SqlEnumType, sa.Enum(name="waitliststatus"))
        confirmation_method_enum.drop(bind, checkfirst=True)
        waitlist_service_enum.drop(bind, checkfirst=True)
        waitlist_status_enum.drop(bind, checkfirst=True)

        op.execute(
            "UPDATE reservations SET status = 'confirmed' WHERE status IN ('pending_confirmation','offered_from_waitlist')"
        )
        op.execute("ALTER TYPE reservationstatus RENAME TO reservationstatus_new")
        op.execute(
            """
            CREATE TYPE reservationstatus AS ENUM (
                'requested',
                'accepted',
                'confirmed',
                'checked_in',
                'checked_out',
                'canceled'
            )
            """
        )
        op.execute(
            """
            ALTER TABLE reservations
            ALTER COLUMN status TYPE reservationstatus
            USING status::text::reservationstatus
            """
        )
        op.execute("DROP TYPE reservationstatus_new")
    else:
        op.execute(
            "UPDATE reservations SET status = 'confirmed' WHERE status IN ('pending_confirmation','offered_from_waitlist')"
        )

    legacy_waitlist_status = cast(
        SqlEnumType,
        sa.Enum(
            "pending",
            "offered",
            "confirmed",
            "canceled",
            name="waitliststatus",
            create_type=False,
        ),
    )
    if dialect == "postgresql":
        legacy_pg_enum = cast(postgresql.ENUM, legacy_waitlist_status)
        legacy_pg_enum.create(bind, checkfirst=True)
        legacy_pg_enum.create_type = False

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
            "status", legacy_waitlist_status, nullable=False, server_default="pending"
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
