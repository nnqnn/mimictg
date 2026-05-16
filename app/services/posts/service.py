from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GeneratedPost, GeneratedPostStatus, User, Workspace
from app.db.repositories.content import get_latest_style_profile
from app.db.repositories.workspaces import get_source_posts
from app.services.ai.schemas import model_to_dict
from app.services.ai.tasks import AITasks
from app.services.tariffs.service import TariffService


class MissingStyleProfileError(RuntimeError):
    pass


class PostService:
    def __init__(self, ai: AITasks, tariffs: TariffService):
        self.ai = ai
        self.tariffs = tariffs

    async def generate_post(
        self,
        session: AsyncSession,
        *,
        user: User,
        workspace: Workspace,
        topic: str,
        post_type: str,
    ) -> GeneratedPost:
        await self.tariffs.ensure_can_generate(session, user)
        profile = await get_latest_style_profile(session, workspace.id)
        if not profile:
            raise MissingStyleProfileError("Сначала нужно обучить стиль канала.")
        source_posts = await get_source_posts(session, workspace.id, limit=8)
        payload = {
            "style_profile": profile.profile_json,
            "source_posts": [post.text for post in source_posts],
            "user_topic": topic,
            "post_type": post_type,
            "channel_goal": user.settings.get("channel_goal"),
            "product_info": user.settings.get("product_info"),
            "user_preferences": user.settings,
        }
        generated = await self.ai.generate_post(payload)
        post = GeneratedPost(
            user_id=user.id,
            workspace_id=workspace.id,
            prompt_text=topic,
            post_type=post_type,
            post_text=generated.post_text,
            status=GeneratedPostStatus.DRAFT,
            ai_metadata=model_to_dict(generated),
        )
        session.add(post)
        await self.tariffs.register_generation(session, user)
        await session.flush()
        return post

    async def improve_post(
        self,
        session: AsyncSession,
        *,
        user: User,
        workspace: Workspace,
        current_post: GeneratedPost,
        action: str,
    ) -> GeneratedPost:
        self.tariffs.require_feature(user.subscription_plan, "improvements")
        profile = await get_latest_style_profile(session, workspace.id)
        if not profile:
            raise MissingStyleProfileError("Сначала нужно обучить стиль канала.")
        improved = await self.ai.improve_post(
            {
                "current_post": current_post.post_text,
                "action": action,
                "style_profile": profile.profile_json,
                "user_preferences": user.settings,
            }
        )
        current_post.post_text = improved.post_text
        current_post.ai_metadata = {
            **(current_post.ai_metadata or {}),
            "last_improvement": model_to_dict(improved),
            "last_action": action,
        }
        await session.flush()
        return current_post


def format_generated_post(post: GeneratedPost) -> str:
    return f"Пост готов.\n\n{post.post_text}"

