# Mimic

Mimic — AI-контент-менеджер для Telegram.

MVP помогает владельцу Telegram-канала обучить стиль по старым постам, создать “паспорт стиля”, генерировать новые посты, улучшать черновики, получать идеи, вести медиа-план, делать аудит и публиковать посты после подтверждения.

## Стек

- Python 3.11+
- aiogram 3
- PostgreSQL
- SQLAlchemy 2 async
- Alembic
- FastAPI + Jinja2 admin panel
- DeepSeek API, модель `deepseek-v4-flash`
- APScheduler
- Docker Compose
- pytest

## Быстрый запуск

1. Создайте `.env`:

```bash
cp .env.example .env
```

2. Заполните:

- `BOT_TOKEN`
- `DEEPSEEK_API_KEY`
- `ADMIN_SESSION_SECRET`
- `ADMIN_LOGIN`
- `ADMIN_PASSWORD`

3. Запустите:

```bash
docker compose up --build
```

4. Админка:

```text
http://localhost:18080
```

Первый вход создаёт admin user из `ADMIN_LOGIN` и `ADMIN_PASSWORD`.

## Миграции

```bash
alembic upgrade head
```

## Бот

Основные команды:

- `/start`
- `/menu`
- `/help`
- `/cancel`
- `/delete_me`
- `/admin`

Главное меню:

- “➕ Мои каналы”
- “✍️ Создать пост”
- “💡 Идеи”
- “📅 Ежедневный пост”
- “📌 Медиа-план”
- “🔎 Аудит”
- “⚙️ Настройки”

## Публичный парсер

Существующий парсер в `tgpars/main.py` сохранён. Wrapper находится в `app/services/parser/telegram_public.py` и возвращает единый формат `ParsedPost`.

`tgpars/venv/` не используется приложением и исключён через `.gitignore`.

## AI pipeline

Все промпты лежат в `prompts/`.

JSON-задачи валидируются Pydantic-схемами. Если DeepSeek вернул невалидный JSON, сервис делает один repair retry.

После генерации поста запускается внутренний `quality_check`. Если score ниже порога `AI_QUALITY_THRESHOLD`, Mimic один раз улучшает пост автоматически.

## Тарифы

- Free: 1 канал, 3 генерации, 1 короткий аудит, без публикации.
- Start: 1 канал, 50 генераций/мес, идеи и улучшения.
- Pro: 2 канала, daily post, медиа-план, публикация, полный аудит.
- Business: 5 каналов, priority flag, задел под будущий агентский режим.

Оплаты пока mock. Тариф можно менять вручную в админке.

## Тесты

```bash
pip install -e ".[dev]"
pytest
```
