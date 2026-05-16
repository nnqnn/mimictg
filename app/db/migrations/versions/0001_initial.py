"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255)),
        sa.Column("first_name", sa.String(255)),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Europe/Moscow"),
        sa.Column("subscription_plan", sa.String(32), nullable=False, server_default="free"),
        sa.Column("subscription_until", sa.DateTime(timezone=True)),
        sa.Column("free_generations_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("free_audit_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("settings", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("privacy_accepted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("channel_type", sa.String(32), nullable=False),
        sa.Column("channel_username", sa.String(255)),
        sa.Column("channel_url", sa.String(1024)),
        sa.Column("telegram_channel_id", sa.BigInteger()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_workspaces_user_id", "workspaces", ["user_id"])
    op.create_index("ix_workspaces_channel_username", "workspaces", ["channel_username"])

    op.create_table(
        "source_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True)),
        sa.Column("views", sa.Integer()),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("raw", jsonb),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_source_posts_workspace_id", "source_posts", ["workspace_id"])

    op.create_table(
        "style_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_json", jsonb, nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("confidence", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_style_profiles_workspace_id", "style_profiles", ["workspace_id"])

    op.create_table(
        "generated_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("post_type", sa.String(64)),
        sa.Column("post_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("ai_metadata", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_generated_posts_user_id", "generated_posts", ["user_id"])
    op.create_index("ix_generated_posts_workspace_id", "generated_posts", ["workspace_id"])

    op.create_table(
        "content_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("parsed_json", jsonb, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_content_plans_workspace_id", "content_plans", ["workspace_id"])

    op.create_table(
        "scheduled_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("generated_post_id", sa.Integer(), sa.ForeignKey("generated_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_scheduled_posts_workspace_id", "scheduled_posts", ["workspace_id"])
    op.create_index("ix_scheduled_posts_generated_post_id", "scheduled_posts", ["generated_post_id"])
    op.create_index("ix_scheduled_posts_scheduled_at", "scheduled_posts", ["scheduled_at"])

    op.create_table(
        "daily_post_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("suggestion_time", sa.String(5), nullable=False, server_default="12:00"),
        sa.Column("source", sa.String(32), nullable=False, server_default="auto"),
        sa.Column("last_suggested_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("workspace_id", name="uq_daily_post_settings_workspace_id"),
    )
    op.create_index("ix_daily_post_settings_workspace_id", "daily_post_settings", ["workspace_id"])

    op.create_table(
        "audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("audit_type", sa.String(16), nullable=False),
        sa.Column("result_json", jsonb, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audits_workspace_id", "audits", ["workspace_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="mocked"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("metadata_json", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="admin"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "ai_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="SET NULL")),
        sa.Column("task_type", sa.String(128), nullable=False),
        sa.Column("prompt_name", sa.String(255), nullable=False),
        sa.Column("input_json", jsonb, nullable=False),
        sa.Column("output_text", sa.Text()),
        sa.Column("parsed_json", jsonb),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_logs_user_id", "ai_logs", ["user_id"])
    op.create_index("ix_ai_logs_workspace_id", "ai_logs", ["workspace_id"])

    op.create_table(
        "app_error_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="SET NULL")),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", jsonb),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_app_error_logs_user_id", "app_error_logs", ["user_id"])
    op.create_index("ix_app_error_logs_workspace_id", "app_error_logs", ["workspace_id"])


def downgrade() -> None:
    for table in [
        "app_error_logs",
        "ai_logs",
        "admin_users",
        "subscriptions",
        "audits",
        "daily_post_settings",
        "scheduled_posts",
        "content_plans",
        "generated_posts",
        "style_profiles",
        "source_posts",
        "workspaces",
        "users",
    ]:
        op.drop_table(table)

