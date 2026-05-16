from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SourcePost, Workspace


async def list_workspaces(session: AsyncSession, user_id: int) -> list[Workspace]:
    result = await session.execute(
        select(Workspace).where(Workspace.user_id == user_id).order_by(Workspace.created_at.desc())
    )
    return list(result.scalars().all())


async def count_workspaces(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(select(func.count(Workspace.id)).where(Workspace.user_id == user_id))
    return int(result.scalar_one())


async def get_active_workspace(session: AsyncSession, user_id: int) -> Workspace | None:
    result = await session.execute(
        select(Workspace).where(Workspace.user_id == user_id, Workspace.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def set_active_workspace(session: AsyncSession, user_id: int, workspace_id: int) -> None:
    await session.execute(update(Workspace).where(Workspace.user_id == user_id).values(is_active=False))
    await session.execute(
        update(Workspace)
        .where(Workspace.user_id == user_id, Workspace.id == workspace_id)
        .values(is_active=True)
    )


async def create_workspace(session: AsyncSession, workspace: Workspace) -> Workspace:
    await session.execute(update(Workspace).where(Workspace.user_id == workspace.user_id).values(is_active=False))
    workspace.is_active = True
    session.add(workspace)
    await session.flush()
    return workspace


async def delete_workspace(session: AsyncSession, user_id: int, workspace_id: int) -> None:
    await session.execute(delete(Workspace).where(Workspace.user_id == user_id, Workspace.id == workspace_id))


async def replace_source_posts(session: AsyncSession, workspace_id: int, posts: list[SourcePost]) -> None:
    await session.execute(delete(SourcePost).where(SourcePost.workspace_id == workspace_id))
    session.add_all(posts)
    await session.flush()


async def get_source_posts(session: AsyncSession, workspace_id: int, limit: int = 20) -> list[SourcePost]:
    result = await session.execute(
        select(SourcePost)
        .where(SourcePost.workspace_id == workspace_id)
        .order_by(SourcePost.date.desc().nullslast(), SourcePost.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())

