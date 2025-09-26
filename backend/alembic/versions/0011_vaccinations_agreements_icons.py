"""Add immunization, agreement, and icon models."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

immunization_status_enum = postgresql.ENUM(
    "valid",
    "expiring",
    "expired",
    name="immunizationstatus",
    create_type=False,
)

icon_entity_enum = postgresql.ENUM(
    "pet",
    "owner",
    "reservation",
    name="iconentity",
    create_type=False,
)


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("DROP TYPE IF EXISTS iconentity"))
        conn.execute(sa.text("DROP TYPE IF EXISTS immunizationstatus"))
        immunization_status_enum.create(conn, checkfirst=True)
        icon_entity_enum.create(conn, checkfirst=True)

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
            "is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")
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
            "status", immunization_status_enum, nullable=False, server_default="valid"
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

    op.create_table(
        "agreement_templates",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "requires_signature",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
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
        "agreement_signatures",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "agreement_template_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agreement_templates.id", ondelete="CASCADE"),
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
            "signed_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "signed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
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
    )

    op.create_table(
        "icons",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=True),
        sa.Column("color", sa.String(length=16), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("applies_to", icon_entity_enum, nullable=False, server_default="pet"),
        sa.Column("popup_text", sa.String(length=512), nullable=True),
        sa.Column(
            "affects_capacity",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
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
        sa.UniqueConstraint("account_id", "slug", name="uq_icon_slug"),
    )

    op.create_table(
        "owner_icons",
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
            nullable=False,
        ),
        sa.Column(
            "icon_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("icons.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
        sa.UniqueConstraint("owner_id", "icon_id", name="uq_owner_icon"),
    )

    op.create_table(
        "pet_icons",
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
            "icon_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("icons.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
        sa.UniqueConstraint("pet_id", "icon_id", name="uq_pet_icon"),
    )


def downgrade() -> None:
    conn = op.get_bind()

    op.drop_table("pet_icons")
    op.drop_table("owner_icons")
    op.drop_table("icons")
    op.drop_table("agreement_signatures")
    op.drop_table("agreement_templates")
    op.drop_table("immunization_records")
    op.drop_table("immunization_types")

    if conn.dialect.name == "postgresql":
        icon_entity_enum.drop(conn, checkfirst=True)
        immunization_status_enum.drop(conn, checkfirst=True)
