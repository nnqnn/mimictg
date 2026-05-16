from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import get_current_user, require_active_workspace
from app.bot.keyboards.inline import post_actions_keyboard, post_type_keyboard, schedule_options_keyboard
from app.bot.keyboards.reply import main_menu_keyboard
from app.bot.states import GenerationStates, PublishingStates, ScheduleStates
from app.config import Settings
from app.db.models import GeneratedPost, GeneratedPostStatus, ScheduledPost
from app.services.ai.tasks import AITasks
from app.services.posts.service import MissingStyleProfileError, PostService, format_generated_post
from app.services.publishing.service import PublishingError, PublishingService
from app.services.tariffs.service import TariffLimitError, TariffService

router = Router(name="generation")


@router.message(F.text == "✍️ Создать пост")
async def create_post_entry(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, message, settings)
    try:
        await require_active_workspace(session, user)
    except RuntimeError as exc:
        await message.answer(str(exc))
        return
    await state.set_state(GenerationStates.wait_topic)
    await message.answer("О чём написать пост? Можно коротко: тема, мысль, цель, референс.")


@router.message(GenerationStates.wait_topic)
async def receive_topic(message: Message, state: FSMContext) -> None:
    topic = (message.text or "").strip()
    if not topic:
        await message.answer("Пришли тему текстом.")
        return
    await state.update_data(topic=topic)
    await state.set_state(GenerationStates.choose_post_type)
    await message.answer("Выбери тип поста.", reply_markup=post_type_keyboard())


@router.callback_query(GenerationStates.choose_post_type, F.data.startswith("post_type:"))
async def choose_post_type(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    ai: AITasks,
    tariffs: TariffService,
) -> None:
    user = await get_current_user(session, callback, settings)
    workspace = await require_active_workspace(session, user)
    data = await state.get_data()
    topic = data.get("topic", "")
    post_type = callback.data.split(":", 1)[1]
    await callback.message.answer("Генерирую пост в стиле канала.")
    try:
        post = await PostService(ai, tariffs).generate_post(
            session,
            user=user,
            workspace=workspace,
            topic=topic,
            post_type=post_type,
        )
    except (TariffLimitError, MissingStyleProfileError, RuntimeError) as exc:
        await callback.message.answer(str(exc))
        await callback.answer()
        return
    await state.clear()
    await callback.message.answer(format_generated_post(post), reply_markup=post_actions_keyboard(post.id))
    await callback.answer()


@router.callback_query(F.data.startswith("post_action:"))
async def post_action(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    ai: AITasks,
    tariffs: TariffService,
    bot: Bot,
) -> None:
    _, action, post_id_raw = callback.data.split(":")
    user = await get_current_user(session, callback, settings)
    workspace = await require_active_workspace(session, user)
    post = await session.get(GeneratedPost, int(post_id_raw))
    if not post or post.user_id != user.id:
        await callback.answer("Пост не найден.", show_alert=True)
        return

    if action in {"rewrite", "shorter", "more_alive", "add_cta", "closer_to_style"}:
        try:
            updated = await PostService(ai, tariffs).improve_post(
                session,
                user=user,
                workspace=workspace,
                current_post=post,
                action=action,
            )
        except (TariffLimitError, MissingStyleProfileError) as exc:
            await callback.message.answer(str(exc))
            await callback.answer()
            return
        await callback.message.answer(format_generated_post(updated), reply_markup=post_actions_keyboard(updated.id))
    elif action == "save":
        post.status = GeneratedPostStatus.SAVED
        await callback.message.answer("Сохранил пост.")
    elif action == "cancel":
        post.status = GeneratedPostStatus.CANCELLED
        await callback.message.answer("Отменил пост.", reply_markup=main_menu_keyboard())
    elif action == "publish":
        if not (workspace.telegram_channel_id or workspace.channel_username):
            await state.set_state(PublishingStates.wait_channel_binding)
            await state.update_data(post_id=post.id)
            await callback.message.answer(
                "Сначала привяжи канал. Перешли сюда любое сообщение из канала или отправь numeric chat_id."
            )
            await callback.answer()
            return
        try:
            await PublishingService(bot, tariffs).publish_now(user, workspace, post)
            await callback.message.answer("Опубликовал пост в канал.")
        except (PublishingError, TariffLimitError) as exc:
            await callback.message.answer(str(exc))
    elif action == "schedule":
        await callback.message.answer("Когда запланировать пост?", reply_markup=schedule_options_keyboard(post.id))
    await callback.answer()


@router.message(PublishingStates.wait_channel_binding)
async def bind_channel_for_publication(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    tariffs: TariffService,
    bot: Bot,
) -> None:
    user = await get_current_user(session, message, settings)
    workspace = await require_active_workspace(session, user)
    chat_id = None
    origin = getattr(message, "forward_origin", None)
    origin_chat = getattr(origin, "chat", None)
    if origin_chat is not None:
        chat_id = origin_chat.id
        workspace.title = getattr(origin_chat, "title", workspace.title) or workspace.title
    elif message.text and message.text.strip().lstrip("-").isdigit():
        chat_id = int(message.text.strip())
    if chat_id is None:
        await message.answer("Не смог определить канал. Перешли сообщение из канала или отправь numeric chat_id.")
        return
    workspace.telegram_channel_id = chat_id
    try:
        await PublishingService(bot, tariffs).ensure_can_publish(user, workspace)
    except (PublishingError, TariffLimitError) as exc:
        await message.answer(str(exc))
        return
    await state.clear()
    await message.answer("Канал привязан. Теперь можно публиковать посты.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data.startswith("schedule:"))
async def schedule_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    tariffs: TariffService,
) -> None:
    _, option, post_id_raw = callback.data.split(":")
    user = await get_current_user(session, callback, settings)
    try:
        tariffs.require_feature(user.subscription_plan, "publication")
    except TariffLimitError as exc:
        await callback.message.answer(str(exc))
        await callback.answer()
        return
    post_id = int(post_id_raw)
    if option == "manual":
        await state.set_state(ScheduleStates.wait_datetime)
        await state.update_data(post_id=post_id)
        await callback.message.answer("Введи дату и время: 2026-05-12 12:00")
        await callback.answer()
        return
    scheduled_at = _preset_datetime(option, user.timezone)
    await _save_schedule(session, post_id, scheduled_at)
    await callback.message.answer(f"Запланировал на {scheduled_at.strftime('%Y-%m-%d %H:%M')}.")
    await callback.answer()


@router.message(ScheduleStates.wait_datetime)
async def schedule_manual(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, message, settings)
    data = await state.get_data()
    try:
        local_dt = datetime.strptime((message.text or "").strip(), "%Y-%m-%d %H:%M")
        scheduled_at = local_dt.replace(tzinfo=ZoneInfo(user.timezone)).astimezone(ZoneInfo("UTC"))
    except Exception:
        await message.answer("Не понял дату. Формат: 2026-05-12 12:00")
        return
    await _save_schedule(session, int(data["post_id"]), scheduled_at)
    await state.clear()
    await message.answer(f"Запланировал на {scheduled_at.strftime('%Y-%m-%d %H:%M')} UTC.", reply_markup=main_menu_keyboard())


def _preset_datetime(option: str, timezone_name: str) -> datetime:
    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)
    if option == "tomorrow_12":
        target = (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    else:
        hour = 12 if option == "today_12" else 18
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
    return target.astimezone(ZoneInfo("UTC"))


async def _save_schedule(session: AsyncSession, post_id: int, scheduled_at: datetime) -> None:
    post = await session.get(GeneratedPost, post_id)
    if not post:
        raise RuntimeError("Пост не найден.")
    post.status = GeneratedPostStatus.SCHEDULED
    session.add(ScheduledPost(generated_post_id=post.id, workspace_id=post.workspace_id, scheduled_at=scheduled_at))
    await session.flush()
