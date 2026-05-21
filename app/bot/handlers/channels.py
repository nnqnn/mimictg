from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import extract_message_text, get_current_user, require_active_workspace
from app.bot.keyboards.inline import channel_type_keyboard
from app.bot.keyboards.reply import channels_menu_keyboard, main_menu_keyboard, private_training_keyboard
from app.bot.states import AddChannelStates
from app.config import Settings
from app.db.models import SourcePost, SourcePostType, Workspace, WorkspaceType
from app.db.repositories.workspaces import (
    count_workspaces,
    create_workspace,
    delete_workspace,
    get_source_posts,
    list_workspaces,
    replace_source_posts,
    set_active_workspace,
)
from app.services.ai.tasks import AITaskError, AITasks
from app.services.parser import ParsedPost, parse_public_channel
from app.services.parser.telegram_public import PublicChannelParseError, extract_channel_username
from app.services.style.service import StyleService, format_style_profile
from app.services.tariffs.service import TariffLimitError, TariffService

router = Router(name="channels")


@router.message(F.text == "➕ Мои каналы")
async def channels_menu(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, message, settings)
    workspaces = await list_workspaces(session, user.id)
    if not workspaces:
        await message.answer("Каналов пока нет. Добавь первый канал.", reply_markup=channels_menu_keyboard())
        return
    active = next((w for w in workspaces if w.is_active), workspaces[0])
    await message.answer(
        f"Активный канал: {active.title}\nВсего каналов: {len(workspaces)}",
        reply_markup=channels_menu_keyboard(),
    )


@router.message(F.text == "➕ Добавить канал")
async def add_channel(message: Message, state: FSMContext, session: AsyncSession, settings: Settings, tariffs: TariffService) -> None:
    user = await get_current_user(session, message, settings)
    current_count = await count_workspaces(session, user.id)
    if not tariffs.can_add_workspace(user.subscription_plan, current_count):
        await message.answer("Лимит каналов на текущем тарифе исчерпан.")
        return
    await state.set_state(AddChannelStates.choose_type)
    await message.answer("Какой канал добавляем?", reply_markup=channel_type_keyboard())


@router.callback_query(AddChannelStates.choose_type, F.data == "channel:type:public")
async def choose_public_channel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddChannelStates.public_url)
    await callback.message.answer("Отправь ссылку на публичный канал: @channel или https://t.me/channel")
    await callback.answer()


@router.callback_query(AddChannelStates.choose_type, F.data == "channel:type:private")
async def choose_private_channel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddChannelStates.private_posts)
    await state.update_data(posts=[])
    await callback.message.answer(
        "Перешли мне до 20 постов из своего канала или просто вставь их текстом.\n"
        "Лучше присылай посты, которые считаешь удачными — по ним я пойму твой стиль.",
        reply_markup=private_training_keyboard(),
    )
    await callback.answer()


@router.message(AddChannelStates.public_url)
async def receive_public_url(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    ai: AITasks,
) -> None:
    user = await get_current_user(session, message, settings)
    channel_url = (message.text or "").strip()
    await message.answer("Принял. Читаю последние посты канала.", reply_markup=ReplyKeyboardRemove())
    try:
        parsed_posts = await parse_public_channel(channel_url, limit=20)
        username = extract_channel_username(channel_url)
    except PublicChannelParseError as exc:
        await message.answer(str(exc))
        return
    if not parsed_posts:
        await message.answer("Не нашёл текстовых постов. Можно попробовать приватное обучение вручную.")
        return
    workspace = Workspace(
        user_id=user.id,
        title=f"@{username}",
        channel_type=WorkspaceType.PUBLIC,
        channel_username=f"@{username}",
        channel_url=f"https://t.me/{username}",
    )
    await create_workspace(session, workspace)
    await replace_source_posts(session, workspace.id, _source_posts_from_parsed(workspace.id, parsed_posts))
    await message.answer(
        f"Я собрал {len(parsed_posts)} постов. Теперь изучаю стиль канала — это может занять до минуты."
    )
    try:
        profile = await StyleService(ai).analyze_workspace_style(
            session,
            user_settings=user.settings,
            workspace_id=workspace.id,
        )
    except AITaskError:
        await state.clear()
        await message.answer(
            "Канал добавлен, но я не смог завершить AI-анализ. Попробуй «Переобучить стиль» чуть позже.",
            reply_markup=channels_menu_keyboard(),
        )
        return
    await state.clear()
    await message.answer(
        "Готово. Я создал паспорт стиля канала.\n\n" + format_style_profile(profile.profile_json),
        reply_markup=channels_menu_keyboard(),
    )


@router.message(AddChannelStates.private_posts, F.text == "🗑 Очистить загруженные посты")
async def clear_private_posts(message: Message, state: FSMContext) -> None:
    await state.update_data(posts=[])
    await message.answer("Очистил загруженные посты. Можно присылать заново.", reply_markup=private_training_keyboard())


@router.message(AddChannelStates.private_posts, F.text == "✅ Завершить обучение")
async def finish_private_training(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    ai: AITasks,
) -> None:
    data = await state.get_data()
    posts = data.get("posts") or []
    if not posts:
        await message.answer("Пока нет текстовых постов для анализа.")
        return
    if len(posts) < 5:
        await message.answer("Постов меньше 5, анализ может быть слабее. Всё равно запускаю обучение.")
    await _create_or_retrain_private_workspace(message, state, session, settings, ai, posts)


@router.message(AddChannelStates.private_posts)
async def collect_private_post(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    ai: AITasks,
    bot: Bot,
) -> None:
    text = extract_message_text(message)
    source_type = SourcePostType.MANUAL_FORWARD if getattr(message, "forward_origin", None) else SourcePostType.MANUAL_TEXT
    if not text and message.document and (message.document.file_name or "").lower().endswith(".txt"):
        downloaded = await bot.download(message.document.file_id)
        if downloaded:
            text = downloaded.read().decode("utf-8", errors="ignore").strip()
            source_type = SourcePostType.FILE
    if not text:
        await message.answer("В этом сообщении нет текста. Я пока анализирую только текстовые посты.")
        return
    data = await state.get_data()
    posts = list(data.get("posts") or [])
    if len(posts) >= 20:
        await message.answer("Я уже собрал 20 постов — запускаю анализ.", reply_markup=ReplyKeyboardRemove())
        await _create_or_retrain_private_workspace(message, state, session, settings, ai, posts)
        return
    posts.append(
        {
            "text": text,
            "source_type": source_type.value,
            "raw": {
                "text_format": "plain_text" if source_type == SourcePostType.FILE else "telegram_html",
            },
        }
    )
    await state.update_data(posts=posts)
    await message.answer(f"Принял пост {len(posts)}/20.", reply_markup=private_training_keyboard())
    if len(posts) >= 20:
        await message.answer("Я собрал 20 постов — этого достаточно для анализа.", reply_markup=ReplyKeyboardRemove())
        await _create_or_retrain_private_workspace(message, state, session, settings, ai, posts)


@router.message(F.text == "🧠 Паспорт стиля")
async def show_style_profile(message: Message, session: AsyncSession, settings: Settings) -> None:
    from app.db.repositories.content import get_latest_style_profile

    user = await get_current_user(session, message, settings)
    try:
        workspace = await require_active_workspace(session, user)
    except RuntimeError as exc:
        await message.answer(str(exc))
        return
    profile = await get_latest_style_profile(session, workspace.id)
    if not profile:
        await message.answer("Паспорт стиля ещё не создан. Добавь посты или переобучи стиль.")
        return
    await message.answer(format_style_profile(profile.profile_json))


@router.message(F.text == "🔀 Сменить активный канал")
async def switch_workspace(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, message, settings)
    workspaces = await list_workspaces(session, user.id)
    if not workspaces:
        await message.answer("Каналов пока нет.")
        return
    lines = ["Твои каналы:"]
    buttons = []
    for workspace in workspaces:
        marker = "•" if workspace.is_active else " "
        lines.append(f"{marker} {workspace.id}: {workspace.title}")
        buttons.append([InlineKeyboardButton(text=workspace.title, callback_data=f"workspace:activate:{workspace.id}")])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("workspace:activate:"))
async def activate_workspace(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, callback, settings)
    workspace_id = int(callback.data.rsplit(":", 1)[1])
    await set_active_workspace(session, user.id, workspace_id)
    await callback.message.answer("Активный канал изменён.")
    await callback.answer()


@router.message(F.text == "🔄 Переобучить стиль")
async def retrain_style(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    ai: AITasks,
) -> None:
    user = await get_current_user(session, message, settings)
    try:
        workspace = await require_active_workspace(session, user)
    except RuntimeError as exc:
        await message.answer(str(exc))
        return
    if workspace.channel_type == WorkspaceType.PUBLIC and workspace.channel_url:
        await message.answer("Обновляю посты и переобучаю стиль.", reply_markup=ReplyKeyboardRemove())
        parsed_posts = await parse_public_channel(workspace.channel_url, limit=20)
        await replace_source_posts(session, workspace.id, _source_posts_from_parsed(workspace.id, parsed_posts))
        profile = await StyleService(ai).analyze_workspace_style(session, user_settings=user.settings, workspace_id=workspace.id)
        await message.answer(format_style_profile(profile.profile_json), reply_markup=channels_menu_keyboard())
        return
    await state.set_state(AddChannelStates.private_posts)
    await state.update_data(posts=[], retrain_workspace_id=workspace.id)
    await message.answer("Пришли новые посты для переобучения.", reply_markup=private_training_keyboard())


@router.message(F.text == "🗑 Удалить канал")
async def delete_active_workspace(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, message, settings)
    try:
        workspace = await require_active_workspace(session, user)
    except RuntimeError as exc:
        await message.answer(str(exc))
        return
    await delete_workspace(session, user.id, workspace.id)
    await message.answer("Канал удалён.", reply_markup=main_menu_keyboard())


def _source_posts_from_parsed(workspace_id: int, posts: list[ParsedPost]) -> list[SourcePost]:
    return [
        SourcePost(
            workspace_id=workspace_id,
            text=post.text,
            date=post.date,
            views=post.views,
            source_type=SourcePostType.PUBLIC_PARSER,
            raw=post.raw,
        )
        for post in posts
    ]


async def _create_or_retrain_private_workspace(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    ai: AITasks,
    posts: list[dict],
) -> None:
    user = await get_current_user(session, message, settings)
    data = await state.get_data()
    workspace_id = data.get("retrain_workspace_id")
    if workspace_id:
        workspace = await session.get(Workspace, workspace_id)
    else:
        workspace = Workspace(
            user_id=user.id,
            title="Приватный канал",
            channel_type=WorkspaceType.PRIVATE,
            is_active=True,
        )
        await create_workspace(session, workspace)
    if not workspace:
        await message.answer("Не нашёл активный канал для переобучения.")
        return
    source_posts = [
        SourcePost(
            workspace_id=workspace.id,
            text=item["text"],
            source_type=SourcePostType(item.get("source_type", SourcePostType.MANUAL_TEXT.value)),
            raw=item.get("raw") or {"text_format": "telegram_html"},
        )
        for item in posts[:20]
    ]
    await replace_source_posts(session, workspace.id, source_posts)
    await message.answer("Принял. Теперь изучаю стиль канала.", reply_markup=ReplyKeyboardRemove())
    try:
        profile = await StyleService(ai).analyze_workspace_style(
            session,
            user_settings=user.settings,
            workspace_id=workspace.id,
        )
    except AITaskError:
        await state.clear()
        await message.answer(
            "Канал добавлен, но я не смог завершить AI-анализ. Попробуй «Переобучить стиль» чуть позже.",
            reply_markup=channels_menu_keyboard(),
        )
        return
    await state.clear()
    await message.answer(
        "Готово. Я создал паспорт стиля канала.\n\n" + format_style_profile(profile.profile_json),
        reply_markup=channels_menu_keyboard(),
    )
