import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import setup_routers
from app.bot.middlewares import DbSessionMiddleware
from app.config import get_settings
from app.services.ai import AITasks, PromptLoader
from app.services.ai.deepseek_provider import DeepSeekProvider
from app.services.scheduler import SchedulerService
from app.services.tariffs import TariffService


async def run_bot() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    tariffs = TariffService(settings)
    ai = AITasks(
        DeepSeekProvider(settings),
        PromptLoader(settings.prompts_dir),
        quality_threshold=settings.ai_quality_threshold,
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.workflow_data.update(settings=settings, tariffs=tariffs, ai=ai)
    dp.include_router(setup_routers())

    scheduler = SchedulerService(bot, tariffs)
    scheduler.start()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await scheduler.shutdown()
        await bot.session.close()

