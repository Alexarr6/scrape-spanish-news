from __future__ import annotations

import re
import unicodedata

_SUSPICIOUS_TOKENS = ("Ã", "Â", "â€")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def _suspicious_score(value: str) -> int:
    return sum(value.count(token) for token in _SUSPICIOUS_TOKENS) + value.count("�")


def _try_mojibake_roundtrip(value: str) -> str:
    # Typical case: UTF-8 bytes decoded as latin-1/cp1252, e.g. "informaciÃ³n".
    try:
        candidate = value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    return candidate if _suspicious_score(candidate) < _suspicious_score(value) else value


def normalize_text(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""

    text = unicodedata.normalize("NFC", text)
    if any(token in text for token in _SUSPICIOUS_TOKENS):
        text = _try_mojibake_roundtrip(text)

    text = _CONTROL_CHARS_RE.sub("", text)
    text = text.replace("�", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text
