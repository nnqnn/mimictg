from aiogram.types import CallbackQuery, Message, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import User, Workspace
from app.db.repositories.users import get_or_create_user
from app.db.repositories.workspaces import get_active_workspace


def tg_user_from_event(event: Message | CallbackQuery) -> TgUser:
    user = event.from_user
    if user is None:
        raise RuntimeError("Telegram user is unavailable")
    return user


async def get_current_user(session: AsyncSession, event: Message | CallbackQuery, settings: Settings) -> User:
    tg_user = tg_user_from_event(event)
    return await get_or_create_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        timezone=settings.default_timezone,
    )


async def require_active_workspace(session: AsyncSession, user: User) -> Workspace:
    workspace = await get_active_workspace(session, user.id)
    if not workspace:
        raise RuntimeError("Сначала добавь канал в разделе «Мои каналы».")
    return workspace


def extract_message_text(message: Message) -> str | None:
    text = message.html_text if (message.text or message.caption) else None
    if text and text.strip():
        return text.strip()
    return None
