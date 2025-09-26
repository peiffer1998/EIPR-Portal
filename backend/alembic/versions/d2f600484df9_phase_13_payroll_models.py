"""phase 13 payroll models"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d2f600484df9"
down_revision = "284d96fbb2ba"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tip_policy_enum = sa.Enum(
        "direct_to_staff",
        "pooled_by_hours",
        "pooled_equal",
        "appointment_direct",
        name="tippolicy",
    )
    bind = op.get_bind()
    tip_policy_enum.create(bind, checkfirst=True)

    op.create_table(
        "payroll_periods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "totals",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "location_id",
            "starts_on",
            "ends_on",
            name="uq_payroll_period",
        ),
    )

    op.create_table(
        "pay_rate_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("ended_on", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pay_rate_history_user", "pay_rate_history", ["user_id"], unique=False
    )

    op.create_table(
        "time_clock_punches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("clock_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clock_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rounded_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rounded_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "minutes_worked", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="web"),
        sa.Column("note", sa.String(length=512), nullable=True),
        sa.Column("payroll_period_id", sa.Uuid(), nullable=True),
        sa.Column(
            "is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["payroll_period_id"], ["payroll_periods.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_timeclock_account_date",
        "time_clock_punches",
        ["account_id", "clock_in_at"],
        unique=False,
    )
    op.create_index(
        "ix_timeclock_user_open", "time_clock_punches", ["user_id"], unique=False
    )

    op.create_table(
        "commission_payouts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("specialist_id", sa.Uuid(), nullable=False),
        sa.Column("basis_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "commission_amount", sa.Numeric(precision=12, scale=2), nullable=False
        ),
        sa.Column("payroll_period_id", sa.Uuid(), nullable=True),
        sa.Column(
            "is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "snapshot",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["appointment_id"], ["grooming_appointments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["payroll_period_id"], ["payroll_periods.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["specialist_id"], ["specialists.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_id", name="uq_commission_by_appointment"),
    )
    op.create_index(
        "ix_commission_specialist",
        "commission_payouts",
        ["specialist_id"],
        unique=False,
    )

    op.create_table(
        "tip_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "source_type", sa.String(length=32), nullable=False, server_default="card"
        ),
        sa.Column("policy", tip_policy_enum, nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=True),
        sa.Column("payment_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("payroll_period_id", sa.Uuid(), nullable=True),
        sa.Column(
            "is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("note", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["appointment_id"], ["grooming_appointments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["payment_transaction_id"], ["payment_transactions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["payroll_period_id"], ["payroll_periods.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tip_tx_date_location",
        "tip_transactions",
        ["date", "location_id"],
        unique=False,
    )

    op.create_table(
        "tip_shares",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tip_transaction_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "method", sa.String(length=32), nullable=False, server_default="direct"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tip_transaction_id"], ["tip_transactions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tip_transaction_id", "user_id", name="uq_tip_share_recipient"
        ),
    )


def downgrade() -> None:
    op.drop_table("tip_shares")
    op.drop_index("ix_tip_tx_date_location", table_name="tip_transactions")
    op.drop_table("tip_transactions")
    op.drop_index("ix_commission_specialist", table_name="commission_payouts")
    op.drop_table("commission_payouts")
    op.drop_index("ix_timeclock_user_open", table_name="time_clock_punches")
    op.drop_index("ix_timeclock_account_date", table_name="time_clock_punches")
    op.drop_table("time_clock_punches")
    op.drop_index("ix_pay_rate_history_user", table_name="pay_rate_history")
    op.drop_table("pay_rate_history")
    op.drop_table("payroll_periods")
    tip_policy_enum = sa.Enum(
        "direct_to_staff",
        "pooled_by_hours",
        "pooled_equal",
        "appointment_direct",
        name="tippolicy",
    )
    tip_policy_enum.drop(op.get_bind(), checkfirst=True)
