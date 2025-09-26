"""Phase 6 pricing rules and promotions."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pricerule_enum = sa.Enum(
        "peak_date",
        "late_checkout",
        "lodging_surcharge",
        "vip",
        name="priceruletype",
    )
    promotion_enum = sa.Enum("percent", "amount", name="promotionkind")

    bind = op.get_bind()
    pricerule_enum.create(bind, checkfirst=True)
    promotion_enum.create(bind, checkfirst=True)

    jsonb_type = postgresql.JSONB(astext_type=sa.Text()).with_variant(
        sa.JSON(), "sqlite"
    )

    op.create_table(
        "price_rules",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule_type", pricerule_enum, nullable=False),
        sa.Column("params", jsonb_type, nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
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

    op.create_table(
        "promotions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("kind", promotion_enum, nullable=False),
        sa.Column("value", sa.Numeric(12, 2), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.UniqueConstraint("account_id", "code", name="uq_promotions_account_code"),
    )


def downgrade() -> None:
    op.drop_table("promotions")
    op.drop_table("price_rules")

    bind = op.get_bind()
    sa.Enum(name="promotionkind").drop(bind, checkfirst=True)
    sa.Enum(name="priceruletype").drop(bind, checkfirst=True)
