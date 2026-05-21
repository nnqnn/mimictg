from aiogram import Router

from app.bot.handlers import admin, audit, channels, common, content_plan, daily, generation, ideas, settings, start, subscription


def setup_routers() -> Router:
    router = Router()
    for child in [
        start.router,
        common.router,
        admin.router,
        channels.router,
        generation.router,
        ideas.router,
        daily.router,
        content_plan.router,
        audit.router,
        subscription.router,
        settings.router,
    ]:
        router.include_router(child)
    return router
