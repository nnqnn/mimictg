from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import get_current_user
from app.bot.keyboards.inline import privacy_keyboard
from app.bot.keyboards.reply import main_menu_keyboard
from app.config import Settings
from app.db.repositories.users import accept_privacy
from app.services.privacy import start_privacy_notice

router = Router(name="start")


ONBOARDING_TEXT = (
    "Mimic — твой AI-контент-менеджер для Telegram.\n\n"
    "Он изучает старые посты канала, запоминает стиль и помогает писать новые публикации так, "
    "будто их подготовил редактор, который давно знает твой блог.\n\n"
    "С чего начать:\n"
    "1. Нажми «➕ Мои каналы» и добавь канал.\n"
    "2. Mimic соберёт паспорт стиля.\n"
    "3. В «✍️ Создать пост» напиши тему — получишь готовый черновик.\n\n"
    "Без подписки можно попробовать базовую генерацию.\n"
    "Pro открывает ежедневные посты, медиа-план, полный аудит и публикацию в канал."
)


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, message, settings)
    if not user.privacy_accepted_at:
        await message.answer(start_privacy_notice(), reply_markup=privacy_keyboard())
        return
    await message.answer(ONBOARDING_TEXT, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "privacy:accept")
async def accept_privacy_callback(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, callback, settings)
    await accept_privacy(session, user)
    await callback.message.answer(ONBOARDING_TEXT, reply_markup=main_menu_keyboard())
    await callback.answer()
