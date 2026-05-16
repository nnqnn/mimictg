import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    START = "start"
    PRO = "pro"
    BUSINESS = "business"


class WorkspaceType(str, enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class SourcePostType(str, enum.Enum):
    PUBLIC_PARSER = "public_parser"
    MANUAL_FORWARD = "manual_forward"
    MANUAL_TEXT = "manual_text"
    FILE = "file"


class GeneratedPostStatus(str, enum.Enum):
    DRAFT = "draft"
    SAVED = "saved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


class ScheduledPostStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class AuditType(str, enum.Enum):
    SHORT = "short"
    FULL = "full"


class PaymentStatus(str, enum.Enum):
    MOCKED = "mocked"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class AdminRole(str, enum.Enum):
    ADMIN = "admin"
    OWNER = "owner"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow", nullable=False)
    subscription_plan: Mapped[SubscriptionPlan] = mapped_column(
        String(32),
        default=SubscriptionPlan.FREE,
        nullable=False,
    )
    subscription_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    free_generations_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    free_audit_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    privacy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workspaces: Mapped[list["Workspace"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    generated_posts: Mapped[list["GeneratedPost"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_type: Mapped[WorkspaceType] = mapped_column(String(32), nullable=False)
    channel_username: Mapped[str | None] = mapped_column(String(255), index=True)
    channel_url: Mapped[str | None] = mapped_column(String(1024))
    telegram_channel_id: Mapped[int | None] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="workspaces")
    source_posts: Mapped[list["SourcePost"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    style_profiles: Mapped[list["StyleProfile"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class SourcePost(Base, TimestampMixin):
    __tablename__ = "source_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    views: Mapped[int | None] = mapped_column(Integer)
    source_type: Mapped[SourcePostType] = mapped_column(String(32), nullable=False)
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    workspace: Mapped[Workspace] = relationship(back_populates="source_posts")


class StyleProfile(Base):
    __tablename__ = "style_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    workspace: Mapped[Workspace] = relationship(back_populates="style_profiles")


class GeneratedPost(Base, TimestampMixin):
    __tablename__ = "generated_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    post_type: Mapped[str | None] = mapped_column(String(64))
    post_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[GeneratedPostStatus] = mapped_column(
        String(32),
        default=GeneratedPostStatus.DRAFT,
        nullable=False,
    )
    ai_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    user: Mapped[User] = relationship(back_populates="generated_posts")


class ContentPlan(Base):
    __tablename__ = "content_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScheduledPost(Base, TimestampMixin):
    __tablename__ = "scheduled_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    generated_post_id: Mapped[int] = mapped_column(ForeignKey("generated_posts.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[ScheduledPostStatus] = mapped_column(
        String(32),
        default=ScheduledPostStatus.PENDING,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text)


class DailyPostSetting(Base):
    __tablename__ = "daily_post_settings"
    __table_args__ = (UniqueConstraint("workspace_id", name="uq_daily_post_settings_workspace_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    suggestion_time: Mapped[str] = mapped_column(String(5), default="12:00", nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="auto", nullable=False)
    last_suggested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Audit(Base, TimestampMixin):
    __tablename__ = "audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    audit_type: Mapped[AuditType] = mapped_column(String(16), nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan: Mapped[SubscriptionPlan] = mapped_column(String(32), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(String(32), default=PaymentStatus.MOCKED, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class AdminUser(Base, TimestampMixin):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[AdminRole] = mapped_column(String(32), default=AdminRole.ADMIN, nullable=False)


class AiLog(Base, TimestampMixin):
    __tablename__ = "ai_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"), index=True)
    task_type: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output_text: Mapped[str | None] = mapped_column(Text)
    parsed_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)


class AppErrorLog(Base, TimestampMixin):
    __tablename__ = "app_error_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"), index=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

