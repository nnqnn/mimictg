from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import get_current_user, require_active_workspace
from app.bot.keyboards.inline import audit_keyboard
from app.config import Settings
from app.db.models import AuditType, SubscriptionPlan
from app.services.ai.tasks import AITasks
from app.services.audit.service import AuditService, format_audit
from app.services.tariffs.service import TariffLimitError, TariffService

router = Router(name="audit")


@router.message(F.text == "🔎 Аудит")
async def audit_entry(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, message, settings)
    try:
        await require_active_workspace(session, user)
    except RuntimeError as exc:
        await message.answer(str(exc))
        return
    is_pro_plus = user.subscription_plan in {SubscriptionPlan.PRO, SubscriptionPlan.BUSINESS}
    await message.answer("Какой аудит сделать?", reply_markup=audit_keyboard(is_pro_plus))


@router.callback_query(F.data.startswith("audit:"))
async def run_audit(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
    ai: AITasks,
    tariffs: TariffService,
) -> None:
    user = await get_current_user(session, callback, settings)
    workspace = await require_active_workspace(session, user)
    audit_type = AuditType.FULL if callback.data.endswith(":full") else AuditType.SHORT
    await callback.message.answer("Смотрю канал и готовлю аудит.")
    try:
        audit = await AuditService(ai, tariffs).run_audit(
            session,
            user=user,
            workspace=workspace,
            audit_type=audit_type,
        )
    except TariffLimitError as exc:
        await callback.message.answer(str(exc))
        await callback.answer()
        return
    await callback.message.answer(format_audit(audit))
    await callback.answer()

