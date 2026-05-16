from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace
from app.db.repositories.content import save_content_plan
from app.services.ai.schemas import model_to_dict
from app.services.ai.tasks import AITasks
from app.services.tariffs.service import TariffService


class ContentPlanService:
    def __init__(self, ai: AITasks, tariffs: TariffService):
        self.ai = ai
        self.tariffs = tariffs

    async def parse_and_save(
        self,
        session: AsyncSession,
        *,
        user: User,
        workspace: Workspace,
        raw_text: str,
    ):
        self.tariffs.require_feature(user.subscription_plan, "media_plan")
        parsed = await self.ai.parse_content_plan({"raw_text": raw_text})
        plan = await save_content_plan(
            session,
            workspace_id=workspace.id,
            raw_text=raw_text,
            parsed_json=model_to_dict(parsed),
        )
        return plan


def format_content_plan_preview(parsed_json: dict) -> str:
    items = parsed_json.get("items") or []
    if not items:
        return "Я не нашёл в плане конкретных постов. Можно отправить план ещё раз."
    lines = ["Я понял план так:"]
    for item in items[:10]:
        date = item.get("date_or_day") or "без даты"
        topic = item.get("topic") or "без темы"
        post_type = item.get("post_type") or "тип не указан"
        lines.append(f"• {date}: {topic} ({post_type})")
    return "\n".join(lines)

