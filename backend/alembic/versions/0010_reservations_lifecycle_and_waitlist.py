"""Add accepted status to reservations lifecycle."""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the accepted status to the reservationstatus enum."""
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.execute("ALTER TYPE reservationstatus ADD VALUE IF NOT EXISTS 'accepted'")


def downgrade() -> None:
    """Remove the accepted status from the reservationstatus enum."""
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.execute("UPDATE reservations SET status = 'requested' WHERE status = 'accepted'")
    op.execute("ALTER TYPE reservationstatus RENAME TO reservationstatus_old")
    op.execute(
        """
        CREATE TYPE reservationstatus AS ENUM (
            'requested',
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
    op.execute("DROP TYPE reservationstatus_old")
