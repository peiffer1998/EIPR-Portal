"""Introduce pricing rules and promotions."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0012"
down_revision = "0011"
branch_labels = ("billing",)
depends_on = None


def upgrade() -> None:
    price_rule_type = sa.Enum(
        "peak_date",
        "late_checkout",
        "lodging_surcharge",
        "vip",
        name="priceruletype",
    )
    price_rule_type.create(op.get_bind(), checkfirst=True)

    promotion_kind = sa.Enum("percent", "amount", name="promotionkind")
    promotion_kind.create(op.get_bind(), checkfirst=True)

    json_type = sa.JSON().with_variant(
        postgresql.JSONB(astext_type=sa.Text()), "postgresql"
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
        sa.Column("rule_type", price_rule_type, nullable=False),
        sa.Column("params", json_type, nullable=False),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
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
        sa.Column("kind", promotion_kind, nullable=False),
        sa.Column("value", sa.Numeric(10, 2), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
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
        sa.UniqueConstraint("account_id", "code", name="uq_promotions_account_code"),
    )


def downgrade() -> None:
    op.drop_table("promotions")
    op.drop_table("price_rules")

    promotion_kind = sa.Enum("percent", "amount", name="promotionkind")
    price_rule_type = sa.Enum(
        "peak_date",
        "late_checkout",
        "lodging_surcharge",
        "vip",
        name="priceruletype",
    )
    promotion_kind.drop(op.get_bind(), checkfirst=True)
    price_rule_type.drop(op.get_bind(), checkfirst=True)
