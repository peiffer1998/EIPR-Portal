"""Add check-in/out fields to reservations."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reservations", sa.Column("kennel_id", sa.Uuid(as_uuid=True), nullable=True)
    )
    op.add_column(
        "reservations",
        sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "reservations",
        sa.Column("check_out_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reservations", "check_out_at")
    op.drop_column("reservations", "check_in_at")
    op.drop_column("reservations", "kennel_id")
