import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.services.ai.prompt_loader import PromptLoader
from app.services.ai.provider import LLMProvider, Message
from app.services.ai.logging import write_ai_log
from app.services.ai.schemas import (
    ContentPlanSchema,
    DailyPostSchema,
    FullAuditSchema,
    GeneratedPostSchema,
    IdeasSchema,
    ImprovedPostSchema,
    QualityCheckSchema,
    ShortAuditSchema,
    StyleProfileSchema,
)


T = TypeVar("T", bound=BaseModel)


class AITaskError(RuntimeError):
    pass


class AITasks:
    def __init__(self, provider: LLMProvider, prompt_loader: PromptLoader, quality_threshold: int = 75):
        self.provider = provider
        self.prompts = prompt_loader
        self.quality_threshold = quality_threshold

    async def analyze_style(self, payload: dict[str, Any]) -> StyleProfileSchema:
        return await self._run_json("analyze_style", payload, StyleProfileSchema, temperature=0.15)

    async def generate_post(self, payload: dict[str, Any]) -> GeneratedPostSchema:
        post = await self._run_json("generate_post", payload, GeneratedPostSchema, temperature=0.55)
        check = await self.quality_check(
            {
                "generated_post": post.post_text,
                "style_profile": payload.get("style_profile"),
                "user_topic": payload.get("user_topic"),
                "post_type": payload.get("post_type"),
            }
        )
        if check.score < self.quality_threshold and check.improvement_instruction:
            improved = await self.improve_post(
                {
                    "current_post": post.post_text,
                    "action": "closer_to_style",
                    "style_profile": payload.get("style_profile"),
                    "user_preferences": payload.get("user_preferences"),
                    "extra_instruction": check.improvement_instruction,
                }
            )
            return GeneratedPostSchema(
                post_text=improved.post_text,
                reasoning_short=post.reasoning_short,
                cta_used=post.cta_used,
                style_notes=post.style_notes + ["Автоулучшение после внутренней проверки качества."],
            )
        return post

    async def improve_post(self, payload: dict[str, Any]) -> ImprovedPostSchema:
        return await self._run_json("improve_post", payload, ImprovedPostSchema, temperature=0.45)

    async def generate_ideas(self, payload: dict[str, Any]) -> IdeasSchema:
        return await self._run_json("generate_ideas", payload, IdeasSchema, temperature=0.55)

    async def audit_short(self, payload: dict[str, Any]) -> ShortAuditSchema:
        return await self._run_json("audit_channel_short", payload, ShortAuditSchema, temperature=0.25)

    async def audit_full(self, payload: dict[str, Any]) -> FullAuditSchema:
        return await self._run_json("audit_channel_full", payload, FullAuditSchema, temperature=0.25)

    async def parse_content_plan(self, payload: dict[str, Any]) -> ContentPlanSchema:
        return await self._run_json("parse_content_plan", payload, ContentPlanSchema, temperature=0.15)

    async def daily_post(self, payload: dict[str, Any]) -> DailyPostSchema:
        return await self._run_json("daily_post", payload, DailyPostSchema, temperature=0.5)

    async def quality_check(self, payload: dict[str, Any]) -> QualityCheckSchema:
        return await self._run_json("quality_check", payload, QualityCheckSchema, temperature=0.1)

    async def _run_json(
        self,
        prompt_name: str,
        payload: dict[str, Any],
        schema: type[T],
        *,
        temperature: float,
    ) -> T:
        prompt = self.prompts.load(prompt_name)
        messages = self._messages(prompt, payload)
        raw = await self.provider.complete_json(messages, temperature=temperature)
        try:
            parsed = self._parse_json(raw, schema)
            await write_ai_log(
                task_type=prompt_name,
                prompt_name=prompt_name,
                input_json=payload,
                output_text=raw,
                parsed_json=parsed.model_dump(),
            )
            return parsed
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as first_error:
            repair_messages = self._repair_messages(prompt, payload, raw, schema, str(first_error))
            repaired = await self.provider.complete_json(repair_messages, temperature=0.05)
            try:
                parsed = self._parse_json(repaired, schema)
                await write_ai_log(
                    task_type=prompt_name,
                    prompt_name=prompt_name,
                    input_json=payload,
                    output_text=repaired,
                    parsed_json=parsed.model_dump(),
                    error=f"repaired after: {first_error}",
                )
                return parsed
            except Exception as second_error:
                await write_ai_log(
                    task_type=prompt_name,
                    prompt_name=prompt_name,
                    input_json=payload,
                    output_text=repaired,
                    error=str(second_error),
                )
                raise AITaskError(
                    f"AI returned invalid JSON for {prompt_name}: {second_error}"
                ) from second_error

    def _messages(self, prompt: str, payload: dict[str, Any]) -> list[Message]:
        return [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": "Входные данные JSON:\n" + json.dumps(payload, ensure_ascii=False, default=str),
            },
        ]

    def _repair_messages(
        self,
        prompt: str,
        payload: dict[str, Any],
        raw_output: str,
        schema: type[T],
        error: str,
    ) -> list[Message]:
        schema_json = schema.model_json_schema()
        return [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    "Предыдущий ответ не прошёл JSON/Pydantic-валидацию.\n"
                    "Верни только исправленный JSON без markdown.\n"
                    f"Ошибка: {error}\n"
                    f"JSON Schema: {json.dumps(schema_json, ensure_ascii=False)}\n"
                    "Исходные входные данные:\n"
                    f"{json.dumps(payload, ensure_ascii=False, default=str)}\n"
                    "Невалидный ответ:\n"
                    f"{raw_output}"
                ),
            },
        ]

    def _parse_json(self, raw: str, schema: type[T]) -> T:
        if not raw or not raw.strip():
            raise ValueError("empty AI response")
        data = json.loads(raw)
        return schema.model_validate(data)
