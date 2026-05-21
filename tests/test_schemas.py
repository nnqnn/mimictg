import pytest
from pydantic import ValidationError

from app.services.ai.schemas import ContentPlanSchema, StyleProfileSchema


def test_content_plan_schema_validation():
    parsed = ContentPlanSchema.model_validate(
        {
            "items": [
                {
                    "date_or_day": "Понедельник",
                    "topic": "Как выбрать тему поста",
                    "post_type": "экспертный",
                    "goal": "вовлечение",
                    "cta": None,
                    "reference": None,
                    "status": "planned",
                }
            ],
            "assumptions": [],
            "missing_info": [],
        }
    )

    assert parsed.items[0].topic == "Как выбрать тему поста"


def test_content_plan_rejects_empty_topic():
    with pytest.raises(ValidationError):
        ContentPlanSchema.model_validate({"items": [{"topic": "   ", "status": "planned"}]})


def test_style_profile_schema_validation():
    profile = StyleProfileSchema.model_validate(
        {
            "summary": "Короткие экспертные посты с мягким CTA.",
            "main_topics": ["контент"],
            "audience": "Владельцы каналов",
            "tone": "спокойный",
            "voice": "профессиональный",
            "typical_length": "средняя",
            "structure_patterns": [],
            "opening_patterns": [],
            "closing_patterns": [],
            "cta_patterns": [],
            "emoji_usage": "редко",
            "formatting_usage": "иногда выделяет ключевые фразы жирным",
            "formatting_patterns": ["точечный <b>акцент</b>"],
            "storytelling_usage": "иногда",
            "expertise_level": "прикладной",
            "sales_style": "мягкий",
            "do_rules": [],
            "dont_rules": [],
            "style_formula": "тезис -> объяснение -> вывод",
            "content_recommendations": [],
            "confidence": 0.8,
        }
    )

    assert profile.confidence == 0.8
    assert profile.formatting_usage.startswith("иногда")
