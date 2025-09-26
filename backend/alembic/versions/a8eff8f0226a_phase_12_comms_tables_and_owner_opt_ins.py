"""phase-12 comms tables and owner opt-ins"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a8eff8f0226a"
down_revision = "2d9a33a5242c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "owner_profiles",
        sa.Column(
            "email_opt_in", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.add_column(
        "owner_profiles",
        sa.Column(
            "sms_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )

    op.create_table(
        "email_templates",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "account_id",
            sa.UUID(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("subject_template", sa.Text(), nullable=False),
        sa.Column("html_template", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "emails_outbox",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "account_id",
            sa.UUID(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            sa.UUID(),
            sa.ForeignKey("owner_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("to_email", sa.Text(), nullable=False),
        sa.Column(
            "template_id",
            sa.UUID(),
            sa.ForeignKey("email_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column(
            "state", sa.String(length=16), nullable=False, server_default="queued"
        ),
        sa.Column("provider_message_id", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state in ('queued','sent','failed')", name="ck_email_outbox_state"
        ),
    )

    op.create_table(
        "sms_conversations",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "account_id",
            sa.UUID(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            sa.UUID(),
            sa.ForeignKey("owner_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phone_e164", sa.String(length=32), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "sms_messages",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "conversation_id",
            sa.UUID(),
            sa.ForeignKey("sms_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider_message_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("direction in ('in','out')", name="ck_sms_direction"),
        sa.CheckConstraint(
            "status in ('queued','sent','delivered','failed','received')",
            name="ck_sms_status",
        ),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "account_id",
            sa.UUID(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(length=8), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "template_id",
            sa.UUID(),
            sa.ForeignKey("email_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("segment", sa.JSON(), nullable=False),
        sa.Column(
            "state", sa.String(length=16), nullable=False, server_default="draft"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("channel in ('email','sms')", name="ck_campaign_channel"),
        sa.CheckConstraint(
            "state in ('draft','sending','done','failed')", name="ck_campaign_state"
        ),
    )

    op.create_table(
        "campaign_sends",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "account_id",
            sa.UUID(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            sa.UUID(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            sa.UUID(),
            sa.ForeignKey("owner_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(length=8), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="queued"
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "channel in ('email','sms')", name="ck_campaign_send_channel"
        ),
        sa.CheckConstraint(
            "status in ('queued','sent','failed')", name="ck_campaign_send_status"
        ),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "account_id",
            sa.UUID(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "type in ('reservation','payment','message','system')",
            name="ck_notifications_type",
        ),
    )

    op.execute(
        "UPDATE owner_profiles SET email_opt_in = TRUE WHERE email_opt_in IS NULL"
    )
    op.execute("UPDATE owner_profiles SET sms_opt_in = FALSE WHERE sms_opt_in IS NULL")
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.alter_column("owner_profiles", "email_opt_in", server_default=None)
        op.alter_column("owner_profiles", "sms_opt_in", server_default=None)


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("campaign_sends")
    op.drop_table("campaigns")
    op.drop_table("sms_messages")
    op.drop_table("sms_conversations")
    op.drop_table("emails_outbox")
    op.drop_table("email_templates")

    op.drop_column("owner_profiles", "sms_opt_in")
    op.drop_column("owner_profiles", "email_opt_in")
