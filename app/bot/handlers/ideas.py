from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import get_current_user, require_active_workspace
from app.bot.keyboards.inline import idea_modes_keyboard
from app.bot.keyboards.reply import main_menu_keyboard
from app.config import Settings
from app.db.repositories.content import get_latest_content_plan, get_latest_style_profile
from app.db.repositories.workspaces import get_source_posts
from app.services.ai.tasks import AITasks
from app.services.tariffs.service import TariffLimitError, TariffService

router = Router(name="ideas")


@router.message(F.text == "💡 Идеи")
async def ideas_menu(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, message, settings)
    try:
        await require_active_workspace(session, user)
    except RuntimeError as exc:
        await message.answer(str(exc))
        return
    await message.answer("Какие идеи подготовить?", reply_markup=idea_modes_keyboard())


@router.callback_query(F.data.startswith("ideas:"))
async def generate_ideas(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
    ai: AITasks,
    tariffs: TariffService,
) -> None:
    user = await get_current_user(session, callback, settings)
    workspace = await require_active_workspace(session, user)
    try:
        tariffs.require_feature(user.subscription_plan, "ideas")
    except TariffLimitError as exc:
        await callback.message.answer(str(exc))
        await callback.answer()
        return
    profile = await get_latest_style_profile(session, workspace.id)
    if not profile:
        await callback.message.answer("Сначала нужно обучить стиль канала.")
        await callback.answer()
        return
    source_posts = await get_source_posts(session, workspace.id, limit=20)
    content_plan = await get_latest_content_plan(session, workspace.id)
    mode = callback.data.split(":", 1)[1]
    await callback.message.answer("Готовлю идеи.", reply_markup=ReplyKeyboardRemove())
    result = await ai.generate_ideas(
        {
            "style_profile": profile.profile_json,
            "channel_goal": user.settings.get("channel_goal"),
            "product_info": user.settings.get("product_info"),
            "previous_topics": [post.text[:180] for post in source_posts],
            "content_plan": content_plan.parsed_json if content_plan else None,
            "idea_mode": mode,
        }
    )
    lines = ["Идеи для постов:"]
    for item in result.ideas:
        lines.append(f"\n• {item.title}\n  {item.angle}\n  Тип: {item.post_type}. Цель: {item.goal}")
    await callback.message.answer("\n".join(lines), reply_markup=main_menu_keyboard())
    await callback.answer()
