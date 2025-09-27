"""merge payroll and waitlist heads"""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "9c5cf6e2bc8d"
down_revision = ("d2f600484df9", "38e1f2fc686b")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op merge migration."""


def downgrade() -> None:
    """No-op merge migration."""
