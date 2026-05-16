from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContentPlan, StyleProfile


async def get_latest_style_profile(session: AsyncSession, workspace_id: int) -> StyleProfile | None:
    result = await session.execute(
        select(StyleProfile)
        .where(StyleProfile.workspace_id == workspace_id)
        .order_by(desc(StyleProfile.updated_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def save_style_profile(
    session: AsyncSession,
    *,
    workspace_id: int,
    profile_json: dict,
    summary: str | None,
    confidence: float | None,
) -> StyleProfile:
    now = datetime.utcnow()
    profile = await get_latest_style_profile(session, workspace_id)
    if profile:
        profile.profile_json = profile_json
        profile.summary = summary
        profile.confidence = confidence
        profile.updated_at = now
    else:
        profile = StyleProfile(
            workspace_id=workspace_id,
            profile_json=profile_json,
            summary=summary,
            confidence=confidence,
            created_at=now,
            updated_at=now,
        )
        session.add(profile)
    await session.flush()
    return profile


async def get_latest_content_plan(session: AsyncSession, workspace_id: int) -> ContentPlan | None:
    result = await session.execute(
        select(ContentPlan)
        .where(ContentPlan.workspace_id == workspace_id)
        .order_by(desc(ContentPlan.updated_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def save_content_plan(
    session: AsyncSession,
    *,
    workspace_id: int,
    raw_text: str,
    parsed_json: dict,
) -> ContentPlan:
    now = datetime.utcnow()
    plan = await get_latest_content_plan(session, workspace_id)
    if plan:
        plan.raw_text = raw_text
        plan.parsed_json = parsed_json
        plan.updated_at = now
    else:
        plan = ContentPlan(
            workspace_id=workspace_id,
            raw_text=raw_text,
            parsed_json=parsed_json,
            created_at=now,
            updated_at=now,
        )
        session.add(plan)
    await session.flush()
    return plan

