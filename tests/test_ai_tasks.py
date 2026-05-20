from datetime import datetime

from app.services.ai.logging import _json_safe
from app.services.ai.prompt_loader import PromptLoader
from app.services.ai.tasks import AITasks


class FakeProvider:
    def __init__(self):
        self.calls = 0

    async def complete_text(self, messages, *, temperature=0.4, max_tokens=None):
        return ""

    async def complete_json(self, messages, *, temperature=0.2, max_tokens=None):
        self.calls += 1
        if self.calls == 1:
            return "not-json"
        return '{"items":[{"date_or_day":"Пн","topic":"Тема","post_type":null,"goal":null,"cta":null,"reference":null,"status":"planned"}],"assumptions":[],"missing_info":[]}'


async def test_ai_tasks_repairs_invalid_json(tmp_path):
    (tmp_path / "parse_content_plan.md").write_text("Return JSON only.", encoding="utf-8")
    tasks = AITasks(FakeProvider(), PromptLoader(tmp_path))

    parsed = await tasks.parse_content_plan({"raw_text": "Пн — Тема"})

    assert parsed.items[0].topic == "Тема"


def test_ai_log_json_safe_converts_datetime():
    payload = {"date": datetime(2026, 5, 21, 2, 30), "nested": [{"ok": True}]}

    safe = _json_safe(payload)

    assert safe["date"] == "2026-05-21 02:30:00"
    assert safe["nested"][0]["ok"] is True
