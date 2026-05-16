from datetime import datetime

import pytest

from app.services.parser.telegram_public import extract_channel_username, normalize_date, normalize_views


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

