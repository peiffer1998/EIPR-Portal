"""Merge health immunization branch with main migration chain."""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "0016_merge_health_branch"
down_revision = ("0014_health", "0015_phase_9_grooming")
branch_labels = None
depends_on = None


def upgrade() -> None:  # pragma: no cover - no-op merge
    pass


def downgrade() -> None:  # pragma: no cover - no-op merge
    pass
