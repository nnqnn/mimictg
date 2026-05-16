from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import Settings

router = Router(name="bot_admin")


@router.message(Command("admin"))
async def admin_command(message: Message, settings: Settings) -> None:
    if message.from_user and message.from_user.id in settings.admin_ids:
        await message.answer("Админ-панель Mimic доступна в FastAPI admin service.")
    else:
        await message.answer("Команда доступна только администратору.")

