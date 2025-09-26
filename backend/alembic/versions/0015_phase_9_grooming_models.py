"""Phase 9 grooming core tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0015_phase_9_grooming"
down_revision = "f02bc10fe274"
branch_labels = None
depends_on = None


commission_enum = postgresql.ENUM(
    "percent", "amount", name="commissiontype", create_type=False
)
appointment_status_enum = postgresql.ENUM(
    "requested",
    "scheduled",
    "checked_in",
    "in_progress",
    "completed",
    "canceled",
    "no_show",
    name="groomingappointmentstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for type_name in ("commissiontype", "groomingappointmentstatus"):
        bind.execute(sa.text(f"DROP TYPE IF EXISTS {type_name}"))

    commission_enum.create(bind, checkfirst=True)
    appointment_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "specialists",
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
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "commission_type", commission_enum, nullable=False, server_default="percent"
        ),
        sa.Column(
            "commission_rate",
            sa.Numeric(6, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
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

    op.create_table(
        "specialist_schedules",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "specialist_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("specialists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(timezone=False), nullable=False),
        sa.Column("end_time", sa.Time(timezone=False), nullable=False),
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

    op.create_table(
        "specialist_time_off",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "specialist_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("specialists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
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

    op.create_table(
        "grooming_services",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.UniqueConstraint("account_id", "code", name="uq_grooming_service_code"),
    )

    op.create_table(
        "grooming_addons",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "add_duration_minutes", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "add_price", sa.Numeric(12, 2), nullable=False, server_default="0.00"
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.UniqueConstraint("account_id", "code", name="uq_grooming_addon_code"),
    )

    op.create_table(
        "grooming_appointments",
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
            sa.ForeignKey("reservations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "owner_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("owner_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pet_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("pets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "specialist_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("specialists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "service_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("grooming_services.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            appointment_status_enum,
            nullable=False,
            server_default="requested",
        ),
        sa.Column("notes", sa.String(length=1024), nullable=True),
        sa.Column("price_snapshot", sa.Numeric(12, 2), nullable=True),
        sa.Column("commission_type", commission_enum, nullable=True),
        sa.Column("commission_rate", sa.Numeric(6, 2), nullable=True),
        sa.Column("commission_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "invoice_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
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

    op.create_index(
        "ix_grooming_appointments_start_at",
        "grooming_appointments",
        ["start_at"],
    )
    op.create_index(
        "ix_grooming_appointments_specialist",
        "grooming_appointments",
        ["specialist_id"],
    )
    op.create_index(
        "ix_grooming_appointments_service",
        "grooming_appointments",
        ["service_id"],
    )

    op.create_table(
        "grooming_appointment_addons",
        sa.Column(
            "appointment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("grooming_appointments.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "addon_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("grooming_addons.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("grooming_appointment_addons")
    op.drop_index(
        "ix_grooming_appointments_service", table_name="grooming_appointments"
    )
    op.drop_index(
        "ix_grooming_appointments_specialist", table_name="grooming_appointments"
    )
    op.drop_index(
        "ix_grooming_appointments_start_at", table_name="grooming_appointments"
    )
    op.drop_table("grooming_appointments")
    op.drop_table("grooming_addons")
    op.drop_table("grooming_services")
    op.drop_table("specialist_time_off")
    op.drop_table("specialist_schedules")
    op.drop_table("specialists")
    bind = op.get_bind()
    appointment_status_enum.drop(bind, checkfirst=True)
    commission_enum.drop(bind, checkfirst=True)
