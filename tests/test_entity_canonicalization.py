from __future__ import annotations

from src.analysis.shared.canonicalization import EntityCanonicalizer
from src.analysis.shared.contracts import ArticleAnalysisExtractedEntity


def test_known_aliases_collapse_to_same_canonical_entity():
    canonicalizer = EntityCanonicalizer()

    psoe = canonicalizer.canonicalize(
        ArticleAnalysisExtractedEntity(entity_type="political_party", canonical_name="PSOE")
    )
    full = canonicalizer.canonicalize(
        ArticleAnalysisExtractedEntity(
            entity_type="political_party", canonical_name="Partido Socialista Obrero Español"
        )
    )
    ue = canonicalizer.canonicalize(
        ArticleAnalysisExtractedEntity(entity_type="institution", canonical_name="UE")
    )

    assert psoe.normalized_name == full.normalized_name == "psoe"
    assert ue.canonical_name == "Unión Europea"
    assert psoe.slug.startswith("political_party-")
