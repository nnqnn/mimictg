import asyncio
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ParsedPost:
    text: str
    date: datetime | None = None
    views: int | None = None
    reactions: dict[str, Any] | None = None
    source_url: str | None = None
    raw: dict[str, Any] | None = None


class PublicChannelParseError(RuntimeError):
    pass


def extract_channel_username(value: str) -> str:
    value = value.strip()
    value = value.removeprefix("@")
    value = re.sub(r"^https?://", "", value)
    value = re.sub(r"^t\.me/", "", value)
    value = re.sub(r"^telegram\.me/", "", value)
    value = re.sub(r"^s/", "", value)
    value = value.split("?")[0].strip("/")
    if "/" in value:
        value = value.split("/")[0]
    if not re.fullmatch(r"[A-Za-z0-9_]{4,}", value):
        raise PublicChannelParseError("Не похоже на ссылку публичного Telegram-канала.")
    return value


def normalize_views(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip().replace(",", ".").replace(" ", "")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([KkMm])?", text)
    if not match:
        digits = re.sub(r"\D", "", text)
        return int(digits) if digits else None
    number = float(match.group(1))
    suffix = match.group(2)
    if suffix and suffix.lower() == "k":
        number *= 1_000
    if suffix and suffix.lower() == "m":
        number *= 1_000_000
    return int(number)


def normalize_date(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_legacy_parser():
    tgpars_dir = Path(__file__).resolve().parents[3] / "tgpars"
    if str(tgpars_dir) not in sys.path:
        sys.path.insert(0, str(tgpars_dir))
    try:
        from main import parse_channel  # type: ignore
    except Exception as exc:  # pragma: no cover - environment dependent
        raise PublicChannelParseError("Не удалось загрузить публичный парсер.") from exc
    return parse_channel


def _normalize_post(raw: dict[str, Any]) -> ParsedPost | None:
    text = (raw.get("text_html") or raw.get("text") or "").strip()
    if not text:
        return None
    raw = {**raw, "text_format": raw.get("text_format") or "telegram_html"}
    return ParsedPost(
        text=text,
        date=normalize_date(raw.get("date")),
        views=normalize_views(raw.get("views")),
        reactions=None,
        source_url=raw.get("url"),
        raw=raw,
    )


def parse_public_channel_sync(channel_url: str, limit: int = 20) -> list[ParsedPost]:
    channel = extract_channel_username(channel_url)
    parser = _load_legacy_parser()
    try:
        raw_posts = parser(channel)
    except Exception as exc:
        raise PublicChannelParseError(
            "Не удалось прочитать публичный канал. Проверь ссылку и доступность канала."
        ) from exc

    posts: list[ParsedPost] = []
    for raw in raw_posts:
        if not isinstance(raw, dict):
            continue
        post = _normalize_post(raw)
        if post:
            posts.append(post)
    return posts[-limit:]


async def parse_public_channel(channel_url: str, limit: int = 20) -> list[ParsedPost]:
    return await asyncio.to_thread(parse_public_channel_sync, channel_url, limit)
