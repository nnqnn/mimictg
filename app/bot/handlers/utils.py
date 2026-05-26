from datetime import datetime, timezone

from aiogram.types import CallbackQuery, Message, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import SubscriptionPlan, User, Workspace
from app.db.repositories.users import get_or_create_user
from app.db.repositories.workspaces import get_active_workspace


ADMIN_SUBSCRIPTION_UNTIL = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)


def tg_user_from_event(event: Message | CallbackQuery) -> TgUser:
    user = event.from_user
    if user is None:
        raise RuntimeError("Telegram user is unavailable")
    return user


async def get_current_user(session: AsyncSession, event: Message | CallbackQuery, settings: Settings) -> User:
    tg_user = tg_user_from_event(event)
    user = await get_or_create_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        timezone=settings.default_timezone,
    )
    if grant_admin_subscription_if_needed(user, settings):
        await session.flush()
    return user


def grant_admin_subscription_if_needed(user: User, settings: Settings) -> bool:
    if user.telegram_id not in settings.admin_ids:
        return False

    changed = False
    if user.subscription_plan != SubscriptionPlan.BUSINESS:
        user.subscription_plan = SubscriptionPlan.BUSINESS
        changed = True

    current_until = user.subscription_until
    if current_until and current_until.tzinfo is None:
        current_until = current_until.replace(tzinfo=timezone.utc)
    if current_until is None or current_until < ADMIN_SUBSCRIPTION_UNTIL:
        user.subscription_until = ADMIN_SUBSCRIPTION_UNTIL
        changed = True
    return changed


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
