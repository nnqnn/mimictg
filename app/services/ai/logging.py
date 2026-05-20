import json
from contextvars import ContextVar
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AiLog


_current_session: ContextVar[AsyncSession | None] = ContextVar("ai_log_session", default=None)


def set_ai_log_session(session: AsyncSession):
    return _current_session.set(session)


def reset_ai_log_session(token) -> None:
    _current_session.reset(token)


async def write_ai_log(
    *,
    task_type: str,
    prompt_name: str,
    input_json: dict[str, Any],
    output_text: str | None,
    parsed_json: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    session = _current_session.get()
    if session is None:
        return
    session.add(
        AiLog(
            task_type=task_type,
            prompt_name=prompt_name,
            input_json=_json_safe(input_json),
            output_text=output_text,
            parsed_json=_json_safe(parsed_json) if parsed_json is not None else None,
            error=error,
        )
    )


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))
