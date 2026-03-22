"""Canonicalize extracted entities so aliases collapse into stable lookup keys."""

from __future__ import annotations

from dataclasses import dataclass

from src.analysis.contracts import ArticleAnalysisExtractedEntity
from src.analysis.normalization import normalize_lookup, slugify

KNOWN_ALIASES: dict[tuple[str, str], tuple[str, tuple[str, ...], str]] = {
    ("political_party", "psoe"): ("PSOE", ("Partido Socialista Obrero Español",), "alias_map"),
    ("political_party", "partido socialista obrero espanol"): (
        "PSOE",
        ("Partido Socialista Obrero Español",),
        "alias_map",
    ),
    ("political_party", "pp"): ("Partido Popular", ("PP",), "alias_map"),
    ("institution", "ue"): ("Unión Europea", ("UE", "Union Europea"), "alias_map"),
    ("institution", "union europea"): ("Unión Europea", ("UE",), "alias_map"),
    ("institution", "generalitat"): ("Generalitat de Catalunya", ("Generalitat",), "alias_map"),
}


@dataclass(frozen=True)
class CanonicalEntity:
    entity_type: str
    canonical_name: str
    normalized_name: str
    slug: str
    canonical_source: str
    aliases: tuple[str, ...] = ()


class EntityCanonicalizer:
    """Apply alias-map rules before falling back to normalized self-canonicalization."""

    def canonicalize(self, entity: ArticleAnalysisExtractedEntity) -> CanonicalEntity:
        normalized = normalize_lookup(entity.canonical_name)
        key = (entity.entity_type, normalized)
        if key in KNOWN_ALIASES:
            canonical_name, aliases, source = KNOWN_ALIASES[key]
            return CanonicalEntity(
                entity_type=entity.entity_type,
                canonical_name=canonical_name,
                normalized_name=normalize_lookup(canonical_name),
                slug=f"{entity.entity_type}-{slugify(canonical_name)}",
                canonical_source=source,
                aliases=aliases,
            )
        return CanonicalEntity(
            entity_type=entity.entity_type,
            canonical_name=entity.canonical_name.strip(),
            normalized_name=normalized,
            slug=f"{entity.entity_type}-{slugify(entity.canonical_name)}",
            canonical_source="rule",
            aliases=tuple(alias.strip() for alias in entity.aliases if alias.strip()),
        )
