from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_or_create_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    timezone: str,
) -> User:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user:
        user.username = username
        user.first_name = first_name
        return user
    user = User(telegram_id=telegram_id, username=username, first_name=first_name, timezone=timezone)
    session.add(user)
    await session.flush()
    return user


async def accept_privacy(session: AsyncSession, user: User) -> None:
    user.privacy_accepted_at = datetime.utcnow()
    await session.flush()


async def delete_user_data(session: AsyncSession, user_id: int) -> None:
    await session.execute(delete(User).where(User.id == user_id))

