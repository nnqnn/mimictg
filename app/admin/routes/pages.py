from datetime import datetime, timedelta, timezone

from aiogram import Bot
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select

from app.admin.auth import authenticate_admin, current_admin
from app.admin.templating import templates
from app.config import get_settings
from app.db.models import (
    AiLog,
    AppErrorLog,
    GeneratedPost,
    Payment,
    PaymentStatus,
    SubscriptionPlan,
    User,
    Workspace,
)
from app.db.session import async_session_factory

router = APIRouter()


def _redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def _require_admin(request: Request) -> bool:
    return current_admin(request) is not None


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def login(request: Request, login: str = Form(...), password: str = Form(...)):
    settings = get_settings()
    async with async_session_factory() as session:
        admin = await authenticate_admin(session, settings, login=login, password=password)
        if not admin:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Неверный логин или пароль"},
                status_code=401,
            )
        await session.commit()
    request.session["admin"] = {"id": admin.id, "login": admin.login, "role": admin.role}
    return _redirect("/")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return _redirect("/login")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not _require_admin(request):
        return _redirect("/login")
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_day = now - timedelta(days=1)
    async with async_session_factory() as session:
        stats = {
            "total_users": await _count(session, select(func.count(User.id))),
            "users_today": await _count(session, select(func.count(User.id)).where(User.created_at >= today)),
            "active_subscriptions": await _count(
                session,
                select(func.count(User.id)).where(User.subscription_plan != SubscriptionPlan.FREE.value),
            ),
            "generations_24h": await _count(
                session,
                select(func.count(GeneratedPost.id)).where(GeneratedPost.created_at >= last_day),
            ),
            "errors_24h": await _count(
                session,
                select(func.count(AppErrorLog.id)).where(AppErrorLog.created_at >= last_day),
            ),
            "payments_pending_24h": await _count(
                session,
                select(func.count(Payment.id)).where(
                    Payment.created_at >= last_day,
                    Payment.status == PaymentStatus.PENDING,
                ),
            ),
            "payments_paid_24h": await _count(
                session,
                select(func.count(Payment.id)).where(
                    Payment.created_at >= last_day,
                    Payment.status == PaymentStatus.PAID,
                ),
            ),
            "payments_problem_24h": await _count(
                session,
                select(func.count(Payment.id)).where(
                    Payment.created_at >= last_day,
                    Payment.status.in_([PaymentStatus.CANCELLED, PaymentStatus.FAILED]),
                ),
            ),
        }
    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats})


@router.get("/users", response_class=HTMLResponse)
async def users(request: Request):
    if not _require_admin(request):
        return _redirect("/login")
    async with async_session_factory() as session:
        result = await session.execute(select(User).order_by(User.created_at.desc()).limit(200))
        users_list = result.scalars().all()
    return templates.TemplateResponse("users.html", {"request": request, "users": users_list})


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: int):
    if not _require_admin(request):
        return _redirect("/login")
    async with async_session_factory() as session:
        user = await session.get(User, user_id)
        result = await session.execute(select(Workspace).where(Workspace.user_id == user_id))
        workspaces = result.scalars().all()
        gen_count = await _count(session, select(func.count(GeneratedPost.id)).where(GeneratedPost.user_id == user_id))
        payments_result = await session.execute(
            select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc()).limit(20)
        )
        payments = payments_result.scalars().all()
    return templates.TemplateResponse(
        "user_detail.html",
        {
            "request": request,
            "user": user,
            "workspaces": workspaces,
            "gen_count": gen_count,
            "plans": SubscriptionPlan,
            "payments": payments,
        },
    )


@router.post("/users/{user_id}/plan")
async def change_plan(request: Request, user_id: int, plan: str = Form(...)):
    if not _require_admin(request):
        return _redirect("/login")
    async with async_session_factory() as session:
        user = await session.get(User, user_id)
        if user:
            user.subscription_plan = SubscriptionPlan(plan)
        await session.commit()
    return _redirect(f"/users/{user_id}")


@router.get("/workspaces", response_class=HTMLResponse)
async def workspaces(request: Request):
    if not _require_admin(request):
        return _redirect("/login")
    async with async_session_factory() as session:
        result = await session.execute(select(Workspace).order_by(Workspace.created_at.desc()).limit(200))
        items = result.scalars().all()
    return templates.TemplateResponse("workspaces.html", {"request": request, "workspaces": items})


@router.get("/logs/ai", response_class=HTMLResponse)
async def ai_logs(request: Request):
    if not _require_admin(request):
        return _redirect("/login")
    async with async_session_factory() as session:
        result = await session.execute(select(AiLog).order_by(AiLog.created_at.desc()).limit(200))
        logs = result.scalars().all()
    return templates.TemplateResponse("ai_logs.html", {"request": request, "logs": logs})


@router.get("/logs/errors", response_class=HTMLResponse)
async def error_logs(request: Request):
    if not _require_admin(request):
        return _redirect("/login")
    async with async_session_factory() as session:
        result = await session.execute(select(AppErrorLog).order_by(AppErrorLog.created_at.desc()).limit(200))
        logs = result.scalars().all()
    return templates.TemplateResponse("error_logs.html", {"request": request, "logs": logs})


@router.get("/broadcast", response_class=HTMLResponse)
async def broadcast_page(request: Request):
    if not _require_admin(request):
        return _redirect("/login")
    return templates.TemplateResponse("broadcast.html", {"request": request, "result": None})


@router.post("/broadcast", response_class=HTMLResponse)
async def broadcast(request: Request, text: str = Form(...)):
    if not _require_admin(request):
        return _redirect("/login")
    settings = get_settings()
    sent = 0
    failed = 0
    bot = Bot(settings.bot_token) if settings.bot_token else None
    async with async_session_factory() as session:
        result = await session.execute(select(User.telegram_id))
        ids = [row[0] for row in result.all()]
    if bot:
        for telegram_id in ids:
            try:
                await bot.send_message(telegram_id, text)
                sent += 1
            except Exception:
                failed += 1
        await bot.session.close()
    return templates.TemplateResponse(
        "broadcast.html",
        {"request": request, "result": f"Отправлено: {sent}. Ошибок: {failed}."},
    )


async def _count(session, statement) -> int:
    result = await session.execute(statement)
    return int(result.scalar_one())
