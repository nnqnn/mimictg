from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import get_current_user, require_active_workspace
from app.bot.keyboards.inline import daily_keyboard, post_actions_keyboard
from app.bot.states import DailyPostStates
from app.config import Settings
from app.db.models import DailyPostSetting, GeneratedPost, GeneratedPostStatus
from app.db.repositories.content import get_latest_content_plan, get_latest_style_profile
from app.db.repositories.workspaces import get_source_posts
from app.services.ai.tasks import AITasks
from app.services.tariffs.service import TariffLimitError, TariffService

router = Router(name="daily")


@router.message(F.text == "📅 Ежедневный пост")
async def daily_entry(
    message: Message,
    session: AsyncSession,
    settings: Settings,
    tariffs: TariffService,
) -> None:
    user = await get_current_user(session, message, settings)
    try:
        workspace = await require_active_workspace(session, user)
        tariffs.require_feature(user.subscription_plan, "daily_post")
    except (RuntimeError, TariffLimitError) as exc:
        await message.answer(str(exc))
        return
    setting = await _get_daily_setting(session, workspace.id, create=True)
    status = "включён" if setting.enabled else "выключен"
    await message.answer(
        f"Ежедневный пост {status}.\nВремя предложения: {setting.suggestion_time}",
        reply_markup=daily_keyboard(setting.enabled),
    )


@router.callback_query(F.data == "daily:toggle")
async def daily_toggle(callback: CallbackQuery, session: AsyncSession, settings: Settings, tariffs: TariffService) -> None:
    user = await get_current_user(session, callback, settings)
    workspace = await require_active_workspace(session, user)
    try:
        tariffs.require_feature(user.subscription_plan, "daily_post")
    except TariffLimitError as exc:
        await callback.message.answer(str(exc))
        await callback.answer()
        return
    setting = await _get_daily_setting(session, workspace.id, create=True)
    setting.enabled = not setting.enabled
    await callback.message.answer("Готово.", reply_markup=daily_keyboard(setting.enabled))
    await callback.answer()


@router.callback_query(F.data == "daily:time")
async def daily_time(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DailyPostStates.wait_time)
    await callback.message.answer("Во сколько присылать ежедневный пост? Формат: 12:00")
    await callback.answer()


@router.message(DailyPostStates.wait_time)
async def save_daily_time(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, message, settings)
    workspace = await require_active_workspace(session, user)
    text = (message.text or "").strip()
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        await message.answer("Не понял время. Формат: 12:00")
        return
    setting = await _get_daily_setting(session, workspace.id, create=True)
    setting.suggestion_time = text
    await state.clear()
    await message.answer("Время сохранено.", reply_markup=daily_keyboard(setting.enabled))


@router.callback_query(F.data == "daily:test")
async def daily_test(callback: CallbackQuery, session: AsyncSession, settings: Settings, ai: AITasks) -> None:
    user = await get_current_user(session, callback, settings)
    workspace = await require_active_workspace(session, user)
    profile = await get_latest_style_profile(session, workspace.id)
    if not profile:
        await callback.message.answer("Сначала нужно обучить стиль канала.")
        await callback.answer()
        return
    posts = await get_source_posts(session, workspace.id, limit=8)
    content_plan = await get_latest_content_plan(session, workspace.id)
    await callback.message.answer("Готовлю тестовый пост.", reply_markup=ReplyKeyboardRemove())
    result = await ai.daily_post(
        {
            "style_profile": profile.profile_json,
            "content_plan_today_item": _pick_plan_item(content_plan.parsed_json if content_plan else None),
            "source_posts": [post.text for post in posts],
            "channel_goal": user.settings.get("channel_goal"),
            "product_info": user.settings.get("product_info"),
            "user_preferences": user.settings,
            "target_date": (datetime.utcnow() + timedelta(days=1)).date().isoformat(),
        }
    )
    post = GeneratedPost(
        user_id=user.id,
        workspace_id=workspace.id,
        prompt_text="Ежедневный пост",
        post_type="daily",
        post_text=result.post_text,
        status=GeneratedPostStatus.DRAFT,
        ai_metadata=result.model_dump(),
    )
    session.add(post)
    await session.flush()
    await callback.message.answer(
        "Тестовый пост готов.\n\n" + post.post_text,
        reply_markup=post_actions_keyboard(post.id),
    )
    await callback.answer()


async def _get_daily_setting(session: AsyncSession, workspace_id: int, create: bool = False) -> DailyPostSetting:
    result = await session.execute(select(DailyPostSetting).where(DailyPostSetting.workspace_id == workspace_id))
    setting = result.scalar_one_or_none()
    if not setting and create:
        setting = DailyPostSetting(workspace_id=workspace_id)
        session.add(setting)
        await session.flush()
    if not setting:
        raise RuntimeError("Daily post settings not found")
    return setting


def _pick_plan_item(parsed_json: dict | None) -> dict | None:
    if not parsed_json:
        return None
    items = parsed_json.get("items") or []
    return items[0] if items else None
