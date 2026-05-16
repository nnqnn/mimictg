from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import get_current_user, require_active_workspace
from app.bot.keyboards.inline import content_plan_confirm_keyboard
from app.bot.keyboards.reply import main_menu_keyboard
from app.bot.states import ContentPlanStates
from app.config import Settings
from app.db.repositories.content import save_content_plan
from app.services.ai.schemas import model_to_dict
from app.services.ai.tasks import AITasks
from app.services.content_plan.service import format_content_plan_preview
from app.services.tariffs.service import TariffLimitError, TariffService

router = Router(name="content_plan")


@router.message(F.text == "📌 Медиа-план")
async def content_plan_entry(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    tariffs: TariffService,
) -> None:
    user = await get_current_user(session, message, settings)
    try:
        await require_active_workspace(session, user)
        tariffs.require_feature(user.subscription_plan, "media_plan")
    except (RuntimeError, TariffLimitError) as exc:
        await message.answer(str(exc))
        return
    await state.set_state(ContentPlanStates.wait_text)
    await message.answer("Отправь медиа-план в свободном виде текстом или .txt файлом.")


@router.message(ContentPlanStates.wait_text)
async def receive_content_plan(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    ai: AITasks,
    bot: Bot,
) -> None:
    text = (message.text or "").strip()
    if not text and message.document and (message.document.file_name or "").lower().endswith(".txt"):
        downloaded = await bot.download(message.document.file_id)
        if downloaded:
            text = downloaded.read().decode("utf-8", errors="ignore").strip()
    if not text:
        await message.answer("Пришли медиа-план текстом или .txt файлом.")
        return
    parsed = await ai.parse_content_plan({"raw_text": text})
    await state.update_data(raw_text=text, parsed_json=model_to_dict(parsed))
    await state.set_state(ContentPlanStates.confirm)
    await message.answer(format_content_plan_preview(model_to_dict(parsed)), reply_markup=content_plan_confirm_keyboard())


@router.callback_query(ContentPlanStates.confirm, F.data == "content_plan:confirm")
async def confirm_content_plan(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, callback, settings)
    workspace = await require_active_workspace(session, user)
    data = await state.get_data()
    await save_content_plan(
        session,
        workspace_id=workspace.id,
        raw_text=data["raw_text"],
        parsed_json=data["parsed_json"],
    )
    await state.clear()
    await callback.message.answer("Медиа-план сохранён.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(ContentPlanStates.confirm, F.data == "content_plan:retry")
async def retry_content_plan(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ContentPlanStates.wait_text)
    await callback.message.answer("Ок, отправь медиа-план заново.")
    await callback.answer()


@router.callback_query(ContentPlanStates.confirm, F.data == "content_plan:clear")
async def clear_content_plan(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Очистил черновик медиа-плана.", reply_markup=main_menu_keyboard())
    await callback.answer()

