from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class StyleProfileSchema(BaseModel):
    summary: str
    main_topics: list[str] = Field(default_factory=list)
    audience: str
    tone: str
    voice: str
    typical_length: str
    structure_patterns: list[str] = Field(default_factory=list)
    opening_patterns: list[str] = Field(default_factory=list)
    closing_patterns: list[str] = Field(default_factory=list)
    cta_patterns: list[str] = Field(default_factory=list)
    emoji_usage: str
    storytelling_usage: str
    expertise_level: str
    sales_style: str
    do_rules: list[str] = Field(default_factory=list)
    dont_rules: list[str] = Field(default_factory=list)
    style_formula: str
    content_recommendations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class GeneratedPostSchema(BaseModel):
    post_text: str = Field(min_length=1)
    reasoning_short: str = ""
    cta_used: bool = False
    style_notes: list[str] = Field(default_factory=list)


class ImprovedPostSchema(BaseModel):
    post_text: str = Field(min_length=1)
    changes_made: list[str] = Field(default_factory=list)


class IdeaItemSchema(BaseModel):
    title: str
    angle: str
    post_type: str
    goal: str
    why_it_fits: str


class IdeasSchema(BaseModel):
    ideas: list[IdeaItemSchema] = Field(min_length=1, max_length=20)


class ShortAuditSchema(BaseModel):
    main_problems: list[str] = Field(default_factory=list)
    quick_recommendations: list[str] = Field(default_factory=list)
    post_ideas: list[str] = Field(default_factory=list)


class FullAuditSchema(BaseModel):
    style_analysis: str
    positioning_analysis: str
    content_strengths: list[str] = Field(default_factory=list)
    content_weaknesses: list[str] = Field(default_factory=list)
    cta_analysis: str
    sales_funnel_analysis: str
    growth_blockers: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    post_ideas: list[str] = Field(default_factory=list)
    seven_day_plan: list[str] = Field(default_factory=list)


class ContentPlanItemSchema(BaseModel):
    date_or_day: str | None = None
    topic: str
    post_type: str | None = None
    goal: str | None = None
    cta: str | None = None
    reference: str | None = None
    status: Literal["planned", "done", "skipped"] = "planned"

    @field_validator("topic")
    @classmethod
    def topic_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("topic is required")
        return value


class ContentPlanSchema(BaseModel):
    items: list[ContentPlanItemSchema] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)


class DailyPostSchema(BaseModel):
    post_text: str = Field(min_length=1)
    reasoning_short: str = ""
    plan_item_used: str | None = None


class QualityCheckSchema(BaseModel):
    is_good: bool
    score: int = Field(ge=0, le=100)
    problems: list[str] = Field(default_factory=list)
    improvement_instruction: str = ""


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    return model.model_dump()

