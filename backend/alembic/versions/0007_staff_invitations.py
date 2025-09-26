"""Add staff invitations table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    invitation_status_enum = postgresql.ENUM(
        "pending",
        "accepted",
        "revoked",
        "expired",
        name="staffinvitationstatus",
        create_type=False,
    )
    op.execute("DROP TYPE IF EXISTS staffinvitationstatus")
    invitation_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "staff_invitations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invited_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("role", sa.Enum(name="userrole"), nullable=False),
        sa.Column(
            "status",
            invitation_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("token_hash", sa.String(length=255), nullable=False, unique=True),
        sa.Column("token_prefix", sa.String(length=16), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
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
        "ix_staff_invitations_account_id",
        "staff_invitations",
        ["account_id"],
    )
    op.create_index(
        "ix_staff_invitations_email",
        "staff_invitations",
        ["email"],
    )


def downgrade() -> None:
    op.drop_index("ix_staff_invitations_email", table_name="staff_invitations")
    op.drop_index("ix_staff_invitations_account_id", table_name="staff_invitations")
    op.drop_table("staff_invitations")
    postgresql.ENUM(name="staffinvitationstatus").drop(op.get_bind(), checkfirst=True)
