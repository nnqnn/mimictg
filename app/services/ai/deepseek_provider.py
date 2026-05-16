from openai import AsyncOpenAI

from app.config import Settings
from app.services.ai.provider import Message


class DeepSeekProvider:
    def __init__(self, settings: Settings):
        if not settings.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for DeepSeekProvider")
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=settings.llm_timeout_seconds,
        )

    async def complete_text(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.4,
        max_tokens: int | None = None,
    ) -> str:
        response = await self._client.chat.completions.create(
            model=self._settings.deepseek_model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            extra_body={"thinking": {"type": "disabled"}},
        )
        return response.choices[0].message.content or ""

    async def complete_json(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        response = await self._client.chat.completions.create(
            model=self._settings.deepseek_model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            stream=False,
            extra_body={"thinking": {"type": "disabled"}},
        )
        return response.choices[0].message.content or ""

