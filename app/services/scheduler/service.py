from datetime import datetime, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import Settings
from app.db.models import GeneratedPost, ScheduledPost, ScheduledPostStatus, User, Workspace
from app.db.session import async_session_factory
from app.services.payments import SubscriptionBillingService, TelegaPayProvider
from app.services.publishing.service import PublishingService
from app.services.tariffs.service import TariffService


class SchedulerService:
    def __init__(self, bot: Bot, tariffs: TariffService, settings: Settings):
        self.bot = bot
        self.tariffs = tariffs
        self.settings = settings
        self.scheduler = AsyncIOScheduler(timezone="UTC")

    def start(self) -> None:
        self.scheduler.add_job(self.send_due_posts, "interval", seconds=60, id="send_due_posts")
        self.scheduler.add_job(
            self.poll_payments,
            "interval",
            seconds=self.settings.payment_poll_interval_seconds,
            id="poll_payments",
        )
        self.scheduler.start()

    async def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)

    async def send_due_posts(self) -> None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(ScheduledPost, GeneratedPost, Workspace, User)
                .join(GeneratedPost, GeneratedPost.id == ScheduledPost.generated_post_id)
                .join(Workspace, Workspace.id == ScheduledPost.workspace_id)
                .join(User, User.id == Workspace.user_id)
                .where(
                    ScheduledPost.status == ScheduledPostStatus.PENDING,
                    ScheduledPost.scheduled_at <= datetime.now(timezone.utc),
                )
                .limit(20)
            )
            publisher = PublishingService(self.bot, self.tariffs)
            for scheduled, post, workspace, user in result.all():
                try:
                    await publisher.publish_now(user, workspace, post)
                    scheduled.status = ScheduledPostStatus.SENT
                except Exception as exc:  # pragma: no cover - integration path
                    scheduled.status = ScheduledPostStatus.FAILED
                    scheduled.error = str(exc)
            await session.commit()

    async def poll_payments(self) -> None:
        service = SubscriptionBillingService(
            self.settings,
            async_session_factory,
            TelegaPayProvider(self.settings),
        )
        await service.poll_pending_payments(self.bot)
