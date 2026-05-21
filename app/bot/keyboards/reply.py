from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="⭐ Подписка")],
        [KeyboardButton(text="➕ Мои каналы"), KeyboardButton(text="✍️ Создать пост")],
        [KeyboardButton(text="💡 Идеи"), KeyboardButton(text="📅 Ежедневный пост")],
        [KeyboardButton(text="📌 Медиа-план"), KeyboardButton(text="🔎 Аудит")],
        [KeyboardButton(text="⚙️ Настройки")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)


def channels_menu_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="➕ Добавить канал")],
        [KeyboardButton(text="🔀 Сменить активный канал"), KeyboardButton(text="🧠 Паспорт стиля")],
        [KeyboardButton(text="🔄 Переобучить стиль"), KeyboardButton(text="🗑 Удалить канал")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def settings_menu_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="Цель канала"), KeyboardButton(text="Что продаю")],
        [KeyboardButton(text="Тональность"), KeyboardButton(text="Эмодзи")],
        [KeyboardButton(text="Длина постов"), KeyboardButton(text="Часовой пояс")],
        [KeyboardButton(text="Подписка"), KeyboardButton(text="Политика конфиденциальности")],
        [KeyboardButton(text="Удалить мои данные")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def private_training_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="✅ Завершить обучение")],
        [KeyboardButton(text="🗑 Очистить загруженные посты")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
