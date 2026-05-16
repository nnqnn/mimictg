from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.reply import main_menu_keyboard
from app.branding import PRODUCT_DESCRIPTION
from app.services.privacy import PRIVACY_POLICY_TEXT

router = Router(name="common")


@router.message(Command("menu"))
@router.message(F.text == "⬅️ Назад")
async def menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню Mimic.", reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        f"{PRODUCT_DESCRIPTION}\n\n"
        "Добавь канал, обучи стиль и создавай посты по теме.\n"
        "Команды: /start, /menu, /cancel, /delete_me."
    )


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменил действие.", reply_markup=main_menu_keyboard())


@router.message(F.text == "Политика конфиденциальности")
async def privacy_policy(message: Message) -> None:
    await message.answer(PRIVACY_POLICY_TEXT)

