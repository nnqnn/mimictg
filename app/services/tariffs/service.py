from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import Audit, AuditType, GeneratedPost, SubscriptionPlan, User


@dataclass(frozen=True)
class TariffLimits:
    workspaces: int
    monthly_generations: int | None
    ideas: bool
    improvements: bool
    daily_post: bool
    media_plan: bool
    publication: bool
    full_audit: bool
    short_audit_limit: int | None
    priority: bool = False


class TariffLimitError(RuntimeError):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class TariffService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def limits_for(self, plan: SubscriptionPlan | str) -> TariffLimits:
        value = plan.value if isinstance(plan, SubscriptionPlan) else plan
        if value == SubscriptionPlan.BUSINESS.value:
            return TariffLimits(5, None, True, True, True, True, True, True, None, True)
        if value == SubscriptionPlan.PRO.value:
            return TariffLimits(2, None, True, True, True, True, True, True, None)
        if value == SubscriptionPlan.START.value:
            return TariffLimits(1, self.settings.start_generations_limit, True, True, False, False, False, False, None)
        return TariffLimits(1, self.settings.free_generations_limit, False, False, False, False, False, False, 1)

    def can_add_workspace(self, plan: SubscriptionPlan | str, current_count: int) -> bool:
        return current_count < self.limits_for(plan).workspaces

    def require_feature(self, plan: SubscriptionPlan | str, feature: str) -> None:
        limits = self.limits_for(plan)
        allowed = bool(getattr(limits, feature))
        if not allowed:
            raise TariffLimitError(self._feature_message(feature))

    async def ensure_can_generate(self, session: AsyncSession, user: User) -> None:
        limits = self.limits_for(user.subscription_plan)
        if limits.monthly_generations is None:
            return
        if user.subscription_plan == SubscriptionPlan.FREE and self.settings.free_generations_period == "all_time":
            used = user.free_generations_used
        else:
            used = await self._monthly_generations_count(session, user.id)
        if used >= limits.monthly_generations:
            plan = "Start или Pro" if user.subscription_plan == SubscriptionPlan.FREE else "Pro"
            raise TariffLimitError(f"Лимит генераций закончился. Можно перейти на {plan}.")

    async def register_generation(self, session: AsyncSession, user: User) -> None:
        if user.subscription_plan == SubscriptionPlan.FREE:
            user.free_generations_used += 1
        await session.flush()

    async def ensure_can_run_audit(self, session: AsyncSession, user: User, audit_type: AuditType, workspace_id: int) -> None:
        if audit_type == AuditType.FULL:
            self.require_feature(user.subscription_plan, "full_audit")
            return
        limits = self.limits_for(user.subscription_plan)
        if limits.short_audit_limit is None:
            return
        result = await session.execute(
            select(func.count(Audit.id)).where(Audit.workspace_id == workspace_id, Audit.audit_type == AuditType.SHORT)
        )
        used = int(result.scalar_one())
        if used >= limits.short_audit_limit or user.free_audit_used:
            raise TariffLimitError("Короткий аудит в бесплатном тарифе уже использован.")

    async def mark_short_audit_used(self, session: AsyncSession, user: User) -> None:
        if user.subscription_plan == SubscriptionPlan.FREE:
            user.free_audit_used = True
            await session.flush()

    async def _monthly_generations_count(self, session: AsyncSession, user_id: int) -> int:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.count(GeneratedPost.id)).where(
                GeneratedPost.user_id == user_id,
                GeneratedPost.created_at >= month_start,
            )
        )
        return int(result.scalar_one())

    def _feature_message(self, feature: str) -> str:
        messages = {
            "daily_post": "Ежедневный пост доступен на Pro и Business.",
            "media_plan": "Медиа-план доступен на Pro и Business.",
            "publication": "Публикация в канал доступна на Pro и Business.",
            "full_audit": "Полный аудит доступен на Pro и Business.",
            "ideas": "Идеи доступны на Start, Pro и Business.",
            "improvements": "Улучшение постов доступно на Start, Pro и Business.",
        }
        return messages.get(feature, "Эта функция недоступна на текущем тарифе.")

