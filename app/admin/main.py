from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.admin.routes import router
from app.config import get_settings


def create_admin_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Mimic Admin")
    app.add_middleware(SessionMiddleware, secret_key=settings.admin_session_secret)
    app.include_router(router)
    return app


app = create_admin_app()
