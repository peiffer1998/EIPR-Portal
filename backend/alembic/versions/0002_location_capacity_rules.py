"""Add location capacity rules table.

Revision ID: 0002
Revises: 0001
Create Date: 2025-09-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "location_capacity_rules",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "location_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reservation_type", sa.Enum(name="reservationtype"), nullable=False),
        sa.Column("max_active", sa.Integer()),
        sa.Column("waitlist_limit", sa.Integer()),
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
            "location_id", "reservation_type", name="uq_capacity_location_type"
        ),
    )


def downgrade() -> None:
    op.drop_table("location_capacity_rules")
