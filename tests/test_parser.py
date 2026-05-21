from datetime import datetime
from pathlib import Path
import sys

import pytest
from aiogram.types import Message
from bs4 import BeautifulSoup

from app.bot.handlers.utils import extract_message_text
from app.services.parser.telegram_public import _normalize_post, extract_channel_username, normalize_date, normalize_views

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tgpars"))
from main import clean_formatted_text  # noqa: E402


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("@durov", "durov"),
        ("https://t.me/durov", "durov"),
        ("https://t.me/s/durov?before=10", "durov"),
        ("t.me/example_channel", "example_channel"),
    ],
)
def test_extract_channel_username(value, expected):
    assert extract_channel_username(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("4.57M", 4_570_000),
        ("12K", 12_000),
        ("123", 123),
        (None, None),
    ],
)
def test_normalize_views(value, expected):
    assert normalize_views(value) == expected


def test_normalize_date_iso():
    parsed = normalize_date("2026-04-13T21:25:34+00:00")

    assert isinstance(parsed, datetime)
    assert parsed.year == 2026


def test_public_parser_preserves_telegram_html_formatting():
    html = (
        '<div>Обычный <strong>жирный</strong><br>'
        '<em>курсив</em> и <a href="https://example.com?a=1&b=2">ссылка</a>'
        '<tg-emoji emoji-id="1"><i><b>❤️</b></i></tg-emoji></div>'
    )
    soup = BeautifulSoup(html, "html.parser")

    assert clean_formatted_text(soup.div) == (
        'Обычный <b>жирный</b>\n'
        '<i>курсив</i> и <a href="https://example.com?a=1&amp;b=2">ссылка</a>❤️'
    )


def test_public_wrapper_prefers_formatted_text():
    post = _normalize_post(
        {
            "text": "Обычный жирный",
            "text_html": "Обычный <b>жирный</b>",
            "date": None,
            "views": None,
        }
    )

    assert post is not None
    assert post.text == "Обычный <b>жирный</b>"
    assert post.raw["text_format"] == "telegram_html"


def test_private_message_entities_are_converted_to_telegram_html():
    message = Message.model_validate(
        {
            "message_id": 1,
            "date": 1_700_000_000,
            "chat": {"id": 1, "type": "private"},
            "text": "hello bold",
            "entities": [{"type": "bold", "offset": 6, "length": 4}],
        }
    )

    assert extract_message_text(message) == "hello <b>bold</b>"
