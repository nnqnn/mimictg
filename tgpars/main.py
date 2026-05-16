import re
import requests
from bs4 import BeautifulSoup


CHANNEL = "durov"


def clean_text(text_el):
    if not text_el:
        return None

    # Telegram хранит реальные абзацы как <br>
    for br in text_el.find_all("br"):
        br.replace_with("\n")

    text = text_el.get_text("", strip=False)

    # чистим пробелы вокруг переносов
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)

    # 3+ переносов подряд -> 2 переноса
    text = re.sub(r"\n{3,}", "\n\n", text)

    # лишние пробелы
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()


def parse_channel(channel: str):
    url = f"https://t.me/s/{channel}"

    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    posts = []

    for msg in soup.select(".tgme_widget_message"):
        post_id = msg.get("data-post")

        text_el = msg.select_one(".tgme_widget_message_text")
        date_el = msg.select_one(".tgme_widget_message_date time[datetime]")
        views_el = msg.select_one(".tgme_widget_message_views")
        link_el = msg.select_one(".tgme_widget_message_date")

        posts.append({
            "id": post_id,
            "url": link_el.get("href") if link_el else None,
            "date": date_el.get("datetime") if date_el else None,
            "views": views_el.get_text(strip=True) if views_el else None,
            "text": clean_text(text_el),
        })

    return posts


if __name__ == "__main__":
    posts = parse_channel(CHANNEL)

    for post in posts:
        print("=" * 80)
        print("ID:", post["id"])
        print("URL:", post["url"])
        print("DATE:", post["date"])
        print("VIEWS:", post["views"])
        print("TEXT:")
        print(post["text"])
