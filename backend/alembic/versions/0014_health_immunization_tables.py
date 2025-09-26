"""Rebuild immunization tables for health track."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0014_health"
down_revision = "0013"
branch_labels = ("health",)
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Drop existing tables from earlier tracks
    op.drop_table("immunization_records")
    op.drop_table("immunization_types")

    if conn.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS immunizationstatus")

    status_enum = sa.Enum(
        "pending",
        "current",
        "expiring",
        "expired",
        name="immunizationstatus",
    )
    if conn.dialect.name == "postgresql":
        status_enum.create(conn, checkfirst=True)

    op.create_table(
        "immunization_types",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("default_valid_days", sa.Integer(), nullable=True),
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
        sa.UniqueConstraint("account_id", "name", name="uq_immunization_type_name"),
    )

    op.create_table(
        "immunization_records",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pet_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("pets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "type_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("immunization_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("issued_on", sa.Date(), nullable=False),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("status", status_enum, nullable=False, server_default="pending"),
        sa.Column(
            "verified_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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


def downgrade() -> None:
    conn = op.get_bind()

    op.drop_table("immunization_records")
    op.drop_table("immunization_types")

    if conn.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS immunizationstatus")

    legacy_status_enum = sa.Enum(
        "valid",
        "expiring",
        "expired",
        name="immunizationstatus",
    )
    if conn.dialect.name == "postgresql":
        legacy_status_enum.create(conn, checkfirst=True)

    op.create_table(
        "immunization_types",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("validity_days", sa.Integer(), nullable=True),
        sa.Column(
            "reminder_days_before", sa.Integer(), nullable=False, server_default="30"
        ),
        sa.Column(
            "is_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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

    op.create_table(
        "immunization_records",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pet_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("pets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "immunization_type_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("immunization_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column(
            "status",
            legacy_status_enum,
            nullable=False,
            server_default="valid",
        ),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(length=512), nullable=True),
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
        sa.UniqueConstraint(
            "account_id",
            "pet_id",
            "immunization_type_id",
            "received_on",
            name="uq_immunization_per_visit",
        ),
    )
