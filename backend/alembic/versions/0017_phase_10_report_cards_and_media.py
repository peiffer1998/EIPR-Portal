"""Phase 10 report cards and media."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0017_phase_10_report_cards_and_media"
down_revision = "0016_merge_health_branch"
branch_labels = None
depends_on = None

report_card_status_enum = sa.Enum(
    "draft",
    "sent",
    name="reportcardstatus",
)


def upgrade() -> None:
    report_card_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "report_cards",
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
            "pet_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("pets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reservation_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("reservations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column(
            "status",
            report_card_status_enum,
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_report_cards_pet_id", "report_cards", ["pet_id"], unique=False)
    op.create_index(
        "ix_report_cards_occurred_on", "report_cards", ["occurred_on"], unique=False
    )

    op.create_table(
        "report_card_media",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "report_card_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("report_cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
            server_default="0",
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
        "ix_report_card_media_card_position",
        "report_card_media",
        ["report_card_id", "position"],
        unique=False,
    )

    op.create_table(
        "report_card_friends",
        sa.Column(
            "report_card_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("report_cards.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "friend_pet_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("pets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.UniqueConstraint(
            "report_card_id", "friend_pet_id", name="uq_report_card_friend"
        ),
    )


def downgrade() -> None:
    op.drop_table("report_card_friends")
    op.drop_index("ix_report_card_media_card_position", table_name="report_card_media")
    op.drop_table("report_card_media")
    op.drop_index("ix_report_cards_occurred_on", table_name="report_cards")
    op.drop_index("ix_report_cards_pet_id", table_name="report_cards")
    op.drop_table("report_cards")
    report_card_status_enum.drop(op.get_bind(), checkfirst=True)
