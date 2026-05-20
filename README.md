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

## Деплой на сервер

Минимальный сервер: Ubuntu 22.04/24.04, Docker, Docker Compose plugin.

1. Установите Docker:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

После этого перелогиньтесь в SSH-сессию.

2. Склонируйте проект:

```bash
git clone <your-repo-url> mimic
cd mimic
```

3. Создайте env-файл:

```bash
cp .env.example .env
nano .env
```

Обязательно заполните:

- `BOT_TOKEN`
- `DEEPSEEK_API_KEY`
- `ADMIN_SESSION_SECRET`
- `ADMIN_LOGIN`
- `ADMIN_PASSWORD`

Для Docker оставьте:

```env
DATABASE_URL=postgresql+asyncpg://mimic:mimic@db:5432/mimic
```

4. Запустите в фоне:

```bash
docker compose up --build -d
```

Если на сервере установлен старый Compose, используйте:

```bash
docker-compose up --build -d
```

5. Проверьте состояние:

```bash
docker compose ps
docker compose logs -f bot
docker compose logs -f admin
```

Для старого Compose:

```bash
docker-compose ps
docker-compose logs -f bot
docker-compose logs -f admin
```

Админка будет доступна на:

```text
http://SERVER_IP:18080
```

PostgreSQL снаружи слушает нестандартный порт `15432`, внутри Docker сеть использует `db:5432`.

6. Обновление после изменений:

```bash
git pull
docker compose up --build -d
```

или:

```bash
git pull
docker-compose up --build -d
```

7. Остановка:

```bash
docker compose down
```

или:

```bash
docker-compose down
```

Данные PostgreSQL лежат в Docker volume `postgres_data` и не удаляются обычным `docker compose down`.

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

Или через requirements:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```
