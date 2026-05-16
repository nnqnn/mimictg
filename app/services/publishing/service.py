from aiogram import Bot

from app.db.models import GeneratedPost, GeneratedPostStatus, User, Workspace
from app.services.tariffs.service import TariffService


class PublishingError(RuntimeError):
    pass


class PublishingService:
    def __init__(self, bot: Bot, tariffs: TariffService):
        self.bot = bot
        self.tariffs = tariffs

    async def ensure_can_publish(self, user: User, workspace: Workspace) -> None:
        self.tariffs.require_feature(user.subscription_plan, "publication")
        chat_id = workspace.telegram_channel_id or workspace.channel_username
        if not chat_id:
            raise PublishingError("Сначала привяжи канал и добавь бота админом.")
        me = await self.bot.get_me()
        member = await self.bot.get_chat_member(chat_id=chat_id, user_id=me.id)
        can_post = getattr(member, "can_post_messages", False)
        if not can_post and getattr(member, "status", "") not in {"creator"}:
            raise PublishingError("У бота нет прав на публикацию. Добавь Mimic админом канала.")

    async def publish_now(self, user: User, workspace: Workspace, post: GeneratedPost) -> None:
        await self.ensure_can_publish(user, workspace)
        chat_id = workspace.telegram_channel_id or workspace.channel_username
        if not chat_id:
            raise PublishingError("Канал не привязан.")
        await self.bot.send_message(chat_id=chat_id, text=post.post_text)
        post.status = GeneratedPostStatus.PUBLISHED

