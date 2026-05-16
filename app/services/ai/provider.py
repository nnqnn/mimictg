from typing import Protocol


Message = dict[str, str]


class LLMProvider(Protocol):
    async def complete_text(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.4,
        max_tokens: int | None = None,
    ) -> str:
        ...

    async def complete_json(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        ...

