"""8C documents: webp fields and sha256."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "f02bc10fe274"
down_revision = "0014_phase_7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("sha256", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("object_key", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("object_key_web", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("bytes_web", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("width", sa.Integer(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("height", sa.Integer(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "content_type_web",
            sa.String(length=128),
            nullable=True,
            server_default="image/webp",
        ),
    )
    op.create_index("ix_documents_sha256", "documents", ["sha256"])


def downgrade() -> None:
    op.drop_index("ix_documents_sha256", table_name="documents")
    op.drop_column("documents", "content_type_web")
    op.drop_column("documents", "height")
    op.drop_column("documents", "width")
    op.drop_column("documents", "bytes_web")
    op.drop_column("documents", "object_key_web")
    op.drop_column("documents", "object_key")
    op.drop_column("documents", "sha256")
