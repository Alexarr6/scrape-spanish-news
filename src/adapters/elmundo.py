from __future__ import annotations

import html
import re

from src.core.models import Article
from src.core.text_normalization import normalize_text

from .rss_adapter import GenericRSSAdapter


class ElMundoAdapter(GenericRSSAdapter):
    source = "elmundo"
    feeds = [
        "https://e00-elmundo.uecdn.es/elmundo/rss/espana.xml",
        "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    ]

    def normalize(self, raw: dict) -> Article:
        article = super().normalize(raw)
        if article.article_text:
            return article

        article.article_text = _read_elmundo_article_body(raw.get("html", ""))
        return article


def _read_elmundo_article_body(page: str) -> str:
    body = _find_article_body_container(page)
    if not body:
        return ""

    paragraphs: list[str] = []
    for match in re.finditer(
        r'<p[^>]*class=["\'][^"\']*ue-c-article__paragraph[^"\']*["\'][^>]*>(.*?)</p>',
        body,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        text = _html_to_text(match.group(1))
        if text:
            paragraphs.append(text)
    return " ".join(paragraphs)


def _find_article_body_container(page: str) -> str:
    marker = re.search(
        r'<div[^>]*class=["\'][^"\']*ue-c-article__body[^"\']*["\'][^>]*>',
        page,
        flags=re.IGNORECASE,
    )
    if marker is None:
        return ""

    start = marker.start()
    pos = marker.end()
    depth = 1
    while depth > 0:
        next_open = re.search(r"<div\b[^>]*>", page[pos:], flags=re.IGNORECASE)
        next_close = re.search(r"</div>", page[pos:], flags=re.IGNORECASE)
        if next_close is None:
            return ""
        close_at = pos + next_close.start()
        open_at = pos + next_open.start() if next_open else None
        if open_at is not None and open_at < close_at:
            depth += 1
            pos = pos + next_open.end()
            continue
        depth -= 1
        pos = pos + next_close.end()

    return page[start:pos]


def _html_to_text(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", fragment, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = normalize_text(text)
    return re.sub(r"\s+([,.;:!?])", r"\1", text)
