"""Heuristic enrichment helpers used as the default analysis fallback path."""

from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher

from src.analysis.contracts import ArticleAnalysisExtractedEntity, ArticleEnrichmentPayload
from src.analysis.taxonomy import SOURCE_TAG_MAP
from src.persistence.contracts import ArticleRead

ARTICLE_TYPE_HINTS = {
    "opinion": ("opinión", "opinion", "tribuna", "columna", "editorial"),
    "analysis": ("análisis", "analysis", "claves", "qué significa", "radiografía"),
    "interview": ("entrevista", "preguntas y respuestas"),
    "live_blog": ("última hora", "directo", "live"),
    "explainer": ("explicado", "explicador", "qué es", "cómo funciona"),
}

TAG_KEYWORDS = {
    "elections": ("elecciones", "campaña", "voto", "urnas"),
    "justice": ("juez", "jueza", "tribunal", "supremo", "fiscalía", "fiscalia"),
    "corruption": ("corrupción", "corrupcion", "mordida", "comisión", "comision"),
    "agreement_negotiation": ("acuerdo", "negociación", "negociacion", "pacto"),
    "statement_reaction": ("reacción", "reaccion", "responde", "replica", "dice"),
    "policy_announcement": ("anuncia", "anuncio", "plan", "medida", "decreto"),
    "protest_social_movement": ("manifestación", "manifestacion", "protesta", "huelga"),
    "security_crime": ("detenido", "crimen", "asesinato", "robo", "policía", "policia"),
    "war_conflict": ("guerra", "ataque", "bombardeo", "frente"),
    "international_eu": ("bruselas", "ue", "unión europea", "union europea"),
    "housing": ("vivienda", "alquiler", "hipoteca"),
    "health": ("hospital", "sanidad", "médico", "medico"),
    "education": ("escuela", "universidad", "alumnos"),
    "transport": ("tren", "renfe", "aeropuerto", "metro"),
    "energy": ("apagón", "apagon", "eléctrica", "electrica", "gas"),
    "sports": ("liga", "partido", "gol", "entrenador"),
}

ENTITY_PATTERNS = (
    ("political_party", re.compile(r"\b(PSOE|PP|Sumar|Podemos|Vox|ERC|Junts|PNV|Bildu)\b", re.I)),
    (
        "institution",
        re.compile(
            (
                r"\b(Congreso|Senado|Gobierno|Fiscalía|Fiscalia|"
                r"Tribunal Supremo|Generalitat|Unión Europea|"
                r"Union Europea|UE)\b"
            ),
            re.I,
        ),
    ),
    ("organization", re.compile(r"\b(ONU|OTAN|RTVE|Renfe|Aemet)\b", re.I)),
    (
        "region_city",
        re.compile(
            r"\b(Madrid|Barcelona|Catalunya|Cataluña|Galicia|Lugo|Valencia|Sevilla|Bilbao|Bruselas)\b",
            re.I,
        ),
    ),
)

PERSON_PATTERN = re.compile(r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)\b")


def infer_article_type(article: ArticleRead) -> tuple[str, float]:
    haystack = " ".join([article.section, article.title, article.summary]).lower()
    for article_type, hints in ARTICLE_TYPE_HINTS.items():
        if any(hint in haystack for hint in hints):
            confidence = 0.95 if article_type in {"opinion", "editorial"} else 0.8
            if article_type == "opinion" and "editorial" in haystack:
                return "editorial", 0.98
            return article_type, confidence
    return "news_report", 0.7


def extract_candidate_entities(article: ArticleRead) -> list[ArticleAnalysisExtractedEntity]:
    text = " ".join([article.title, article.summary, article.article_text])
    seen: dict[tuple[str, str], ArticleAnalysisExtractedEntity] = {}
    counts = Counter(re.findall(r"\w+", text.lower()))
    for entity_type, pattern in ENTITY_PATTERNS:
        for match in pattern.findall(text):
            name = str(match).strip()
            key = (entity_type, name.lower())
            seen[key] = ArticleAnalysisExtractedEntity(
                entity_type=entity_type,
                canonical_name=name,
                relevance_score=0.8 if name in article.title else 0.6,
            )
    for person_name in PERSON_PATTERN.findall(text):
        lower = person_name.lower()
        if lower.split()[0] in {"el", "la", "los", "las"}:
            continue
        key = ("person", lower)
        seen.setdefault(
            key,
            ArticleAnalysisExtractedEntity(
                entity_type="person",
                canonical_name=person_name,
                relevance_score=0.75 if person_name in article.title else 0.55,
            ),
        )
    ranked = sorted(
        seen.values(),
        key=lambda item: (
            item.relevance_score,
            counts.get(item.canonical_name.split()[0].lower(), 0),
        ),
        reverse=True,
    )
    return ranked[:12]


def infer_tag_codes(article: ArticleRead) -> tuple[str | None, list[str]]:
    raw_bits = [article.section, article.tags, article.title, article.summary]
    combined = " | ".join(raw_bits).lower()
    chosen: list[str] = []
    for raw, tag_code in SOURCE_TAG_MAP.items():
        if raw in combined and tag_code not in chosen:
            chosen.append(tag_code)
    for tag_code, keywords in TAG_KEYWORDS.items():
        if any(keyword in combined for keyword in keywords) and tag_code not in chosen:
            chosen.append(tag_code)
    if not chosen:
        return None, []
    return chosen[0], chosen[1:4]


def heuristic_enrichment(article: ArticleRead) -> ArticleEnrichmentPayload:
    """Produce a bounded best-effort enrichment payload without any external model call."""

    article_type, confidence = infer_article_type(article)
    primary_tag, secondary_tags = infer_tag_codes(article)
    key_phrases = [
        phrase.strip() for phrase in re.split(r"[,;:.]", article.title) if phrase.strip()
    ][:3]
    claims = [article.summary.strip()] if article.summary.strip() else []
    return ArticleEnrichmentPayload(
        article_type=article_type,
        article_type_confidence=confidence,
        is_event_coverage=article_type not in {"opinion", "editorial"},
        primary_tag_code=primary_tag,
        secondary_tag_codes=secondary_tags,
        entities=extract_candidate_entities(article),
        key_phrases=key_phrases,
        claims=claims,
    )


def title_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left.lower(), right.lower()).ratio()
