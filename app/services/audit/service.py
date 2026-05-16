from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Audit, AuditType, User, Workspace
from app.db.repositories.content import get_latest_style_profile
from app.db.repositories.workspaces import get_source_posts
from app.services.ai.schemas import model_to_dict
from app.services.ai.tasks import AITasks
from app.services.tariffs.service import TariffService


class AuditService:
    def __init__(self, ai: AITasks, tariffs: TariffService):
        self.ai = ai
        self.tariffs = tariffs

    async def run_audit(
        self,
        session: AsyncSession,
        *,
        user: User,
        workspace: Workspace,
        audit_type: AuditType,
    ) -> Audit:
        await self.tariffs.ensure_can_run_audit(session, user, audit_type, workspace.id)
        profile = await get_latest_style_profile(session, workspace.id)
        posts = await get_source_posts(session, workspace.id, limit=20)
        payload = {
            "style_profile": profile.profile_json if profile else None,
            "source_posts": [post.text for post in posts],
            "channel_goal": user.settings.get("channel_goal"),
            "product_info": user.settings.get("product_info"),
            "user_preferences": user.settings,
        }
        result = await self.ai.audit_full(payload) if audit_type == AuditType.FULL else await self.ai.audit_short(payload)
        audit = Audit(workspace_id=workspace.id, audit_type=audit_type, result_json=model_to_dict(result))
        session.add(audit)
        if audit_type == AuditType.SHORT:
            await self.tariffs.mark_short_audit_used(session, user)
        await session.flush()
        return audit


def format_audit(audit: Audit) -> str:
    data = audit.result_json
    if audit.audit_type == AuditType.SHORT:
        return (
            "Короткий аудит\n\n"
            "Главные проблемы:\n"
            + "\n".join(f"• {x}" for x in data.get("main_problems", []))
            + "\n\nРекомендации:\n"
            + "\n".join(f"• {x}" for x in data.get("quick_recommendations", []))
            + "\n\nИдеи:\n"
            + "\n".join(f"• {x}" for x in data.get("post_ideas", []))
        )
    return (
        "Полный аудит\n\n"
        f"Стиль: {data.get('style_analysis', '—')}\n\n"
        f"Позиционирование: {data.get('positioning_analysis', '—')}\n\n"
        "Рекомендации:\n"
        + "\n".join(f"• {x}" for x in data.get("recommendations", []))
        + "\n\nПлан на 7 дней:\n"
        + "\n".join(f"• {x}" for x in data.get("seven_day_plan", []))
    )

