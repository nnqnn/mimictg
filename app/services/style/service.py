from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.content import save_style_profile
from app.db.repositories.workspaces import get_source_posts
from app.services.ai.schemas import model_to_dict
from app.services.ai.tasks import AITasks


class StyleService:
    def __init__(self, ai: AITasks):
        self.ai = ai

    async def analyze_workspace_style(
        self,
        session: AsyncSession,
        *,
        user_settings: dict,
        workspace_id: int,
    ):
        posts = await get_source_posts(session, workspace_id, limit=20)
        payload = {
            "posts": [{"text": post.text, "date": post.date, "views": post.views} for post in posts],
            "channel_goal": user_settings.get("channel_goal"),
            "product_info": user_settings.get("product_info"),
            "user_preferences": user_settings,
        }
        profile = await self.ai.analyze_style(payload)
        saved = await save_style_profile(
            session,
            workspace_id=workspace_id,
            profile_json=model_to_dict(profile),
            summary=profile.summary,
            confidence=profile.confidence,
        )
        return saved


def format_style_profile(profile_json: dict) -> str:
    return (
        "Паспорт стиля\n\n"
        f"Кратко: {profile_json.get('summary', '—')}\n"
        f"Темы: {', '.join(profile_json.get('main_topics') or []) or '—'}\n"
        f"Тон: {profile_json.get('tone', '—')}\n"
        f"Голос: {profile_json.get('voice', '—')}\n"
        f"Длина: {profile_json.get('typical_length', '—')}\n"
        f"Формула: {profile_json.get('style_formula', '—')}\n"
        f"Уверенность: {round(float(profile_json.get('confidence') or 0) * 100)}%"
    )

