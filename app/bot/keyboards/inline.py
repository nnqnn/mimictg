from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def privacy_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Согласен", callback_data="privacy:accept")]]
    )


def channel_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Публичный канал", callback_data="channel:type:public")],
            [InlineKeyboardButton(text="Приватный канал", callback_data="channel:type:private")],
        ]
    )


def post_type_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for text in ["Экспертный", "Личный", "Продающий", "Прогрев", "История", "Короткий", "Длинный", "Без уточнений"]:
        rows.append([InlineKeyboardButton(text=text, callback_data=f"post_type:{text}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def post_actions_keyboard(post_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="🔁 Переписать", callback_data=f"post_action:rewrite:{post_id}"),
            InlineKeyboardButton(text="✂️ Короче", callback_data=f"post_action:shorter:{post_id}"),
        ],
        [
            InlineKeyboardButton(text="🔥 Живее", callback_data=f"post_action:more_alive:{post_id}"),
            InlineKeyboardButton(text="🎯 Добавить CTA", callback_data=f"post_action:add_cta:{post_id}"),
        ],
        [InlineKeyboardButton(text="🧠 Ближе к моему стилю", callback_data=f"post_action:closer_to_style:{post_id}")],
        [
            InlineKeyboardButton(text="📅 Запланировать", callback_data=f"post_action:schedule:{post_id}"),
            InlineKeyboardButton(text="📤 Опубликовать", callback_data=f"post_action:publish:{post_id}"),
        ],
        [
            InlineKeyboardButton(text="💾 Сохранить", callback_data=f"post_action:save:{post_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"post_action:cancel:{post_id}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def idea_modes_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        ("10 идей на неделю", "week"),
        ("Идеи по моему стилю", "style"),
        ("Идеи для продаж", "sales"),
        ("Идеи для вовлечения", "engagement"),
        ("Идеи по медиа-плану", "plan"),
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=f"ideas:{mode}")] for text, mode in buttons]
    )


def content_plan_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="content_plan:confirm")],
            [InlineKeyboardButton(text="✏️ Отправить заново", callback_data="content_plan:retry")],
            [InlineKeyboardButton(text="🗑 Очистить", callback_data="content_plan:clear")],
        ]
    )


def audit_keyboard(is_pro_plus: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="Короткий аудит", callback_data="audit:short")]]
    if is_pro_plus:
        rows.append([InlineKeyboardButton(text="Полный аудит", callback_data="audit:full")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def daily_keyboard(enabled: bool = False) -> InlineKeyboardMarkup:
    toggle = "Выключить" if enabled else "Включить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle, callback_data="daily:toggle")],
            [InlineKeyboardButton(text="Время предложения", callback_data="daily:time")],
            [InlineKeyboardButton(text="Тестовый пост на завтра", callback_data="daily:test")],
        ]
    )


def schedule_options_keyboard(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Сегодня 12:00", callback_data=f"schedule:today_12:{post_id}")],
            [InlineKeyboardButton(text="Сегодня 18:00", callback_data=f"schedule:today_18:{post_id}")],
            [InlineKeyboardButton(text="Завтра 12:00", callback_data=f"schedule:tomorrow_12:{post_id}")],
            [InlineKeyboardButton(text="Ввести вручную", callback_data=f"schedule:manual:{post_id}")],
        ]
    )

