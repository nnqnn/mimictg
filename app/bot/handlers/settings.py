from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import get_current_user
from app.bot.keyboards.reply import main_menu_keyboard, settings_menu_keyboard
from app.bot.states import DeleteDataStates, SettingsStates
from app.config import Settings
from app.db.repositories.users import delete_user_data
from app.services.privacy import PRIVACY_POLICY_TEXT

router = Router(name="settings")


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message) -> None:
    await message.answer("Настройки Mimic.", reply_markup=settings_menu_keyboard())


@router.message(F.text == "Цель канала")
async def channel_goal(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsStates.wait_channel_goal)
    await message.answer(
        "Выбери или напиши цель канала:\n"
        "Продавать услуги\nРазвивать личный бренд\nНабирать аудиторию\n"
        "Вести экспертный блог\nПродавать продукты/курсы\nДругое"
    )


@router.message(F.text == "Что продаю")
async def product_info(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsStates.wait_product_info)
    await message.answer("Что ты продаёшь или продвигаешь? Можно коротко.")


@router.message(F.text == "Тональность")
async def tone(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsStates.wait_tone)
    await message.answer("Какую тональность держать? Например: спокойно, уверенно, живо.")


@router.message(F.text == "Эмодзи")
async def emoji(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsStates.wait_emoji)
    await message.answer("Как использовать эмодзи? Например: редко, умеренно, без эмодзи.")


@router.message(F.text == "Длина постов")
async def length(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsStates.wait_length)
    await message.answer("Какая длина постов комфортна? Короткие, средние или длинные.")


@router.message(F.text == "Часовой пояс")
async def timezone(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsStates.wait_timezone)
    await message.answer("Укажи часовой пояс. Например: Europe/Moscow")


@router.message(F.text == "Подписка")
async def subscription(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, message, settings)
    await message.answer(f"Текущий тариф: {user.subscription_plan}.")


@router.message(F.text == "Политика конфиденциальности")
async def policy(message: Message) -> None:
    await message.answer(PRIVACY_POLICY_TEXT)


@router.message(Command("delete_me"))
@router.message(F.text == "Удалить мои данные")
async def delete_me_start(message: Message, state: FSMContext) -> None:
    await state.set_state(DeleteDataStates.confirm)
    await message.answer("Это удалит данные Mimic. Напиши УДАЛИТЬ для подтверждения.")


@router.message(DeleteDataStates.confirm)
async def delete_me_confirm(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    if (message.text or "").strip() != "УДАЛИТЬ":
        await message.answer("Удаление отменено.", reply_markup=main_menu_keyboard())
        await state.clear()
        return
    user = await get_current_user(session, message, settings)
    await delete_user_data(session, user.id)
    await state.clear()
    await message.answer("Данные удалены.")


@router.message(SettingsStates.wait_channel_goal)
async def save_goal(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    await _save_setting(message, state, session, settings, "channel_goal")


@router.message(SettingsStates.wait_product_info)
async def save_product(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    await _save_setting(message, state, session, settings, "product_info")


@router.message(SettingsStates.wait_tone)
async def save_tone(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    await _save_setting(message, state, session, settings, "tone")


@router.message(SettingsStates.wait_emoji)
async def save_emoji(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    await _save_setting(message, state, session, settings, "emoji")


@router.message(SettingsStates.wait_length)
async def save_length(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    await _save_setting(message, state, session, settings, "post_length")


@router.message(SettingsStates.wait_timezone)
async def save_timezone(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, message, settings)
    value = (message.text or "").strip()
    if "/" not in value:
        await message.answer("Похоже, это не часовой пояс. Пример: Europe/Moscow")
        return
    user.timezone = value
    await state.clear()
    await message.answer("Часовой пояс сохранён.", reply_markup=settings_menu_keyboard())


async def _save_setting(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    key: str,
) -> None:
    user = await get_current_user(session, message, settings)
    user_settings = dict(user.settings or {})
    user_settings[key] = (message.text or "").strip()
    user.settings = user_settings
    await state.clear()
    await message.answer("Сохранил.", reply_markup=settings_menu_keyboard())

