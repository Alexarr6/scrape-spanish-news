from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

TITLE_NOISE = {
    "presidente",
    "presidenta",
    "ministro",
    "ministra",
    "portavoz",
    "señor",
    "señora",
    "sr",
    "sra",
    "don",
    "doña",
}


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_lookup(value: str) -> str:
    text = strip_accents(value or "").lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = [token for token in text.split() if token and token not in TITLE_NOISE]
    return " ".join(tokens)


def slugify(value: str) -> str:
    text = normalize_lookup(value)
    text = re.sub(r"\s+", "-", text)
    return text.strip("-")[:120]


def jaccard_similarity(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = {item for item in left if item}
    right_set = {item for item in right if item}
    if not left_set and not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)
