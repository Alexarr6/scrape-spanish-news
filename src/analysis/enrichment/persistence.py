from __future__ import annotations

import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.analysis.shared.canonicalization import EntityCanonicalizer
from src.analysis.shared.contracts import (
    ArticleAnalysisExtractedEntity,
    ArticleEnrichmentPayload,
)
from src.analysis.shared.normalization import normalize_lookup
from src.analysis.store.models import (
    ArticleAnalysisORM,
    ArticleTagORM,
    EntityAliasORM,
    EntityMentionORM,
    EntityORM,
    TagORM,
)
from src.analysis.shared.taxonomy import CANONICAL_TAGS
from src.persistence.core import ArticleRead


def seed_tags(session: Session) -> None:
    existing = {row.tag_code: row for row in session.execute(select(TagORM)).scalars()}
    for tag in CANONICAL_TAGS:
        row = existing.get(tag.code)
        if row is None:
            session.add(
                TagORM(
                    tag_code=tag.code,
                    display_name=tag.display_name,
                    tag_group=tag.group,
                    description=tag.description,
                    sort_order=tag.sort_order,
                )
            )
        else:
            row.display_name = tag.display_name
            row.tag_group = tag.group
            row.description = tag.description
            row.sort_order = tag.sort_order
            row.is_active = True
    session.commit()


class ArticleAnalysisPersister:
    def __init__(self, session: Session, *, canonicalizer: EntityCanonicalizer) -> None:
        self.session = session
        self.canonicalizer = canonicalizer

    def persist_article_analysis(
        self,
        *,
        article: ArticleRead,
        payload: ArticleEnrichmentPayload,
        tag_by_code: dict[str, int],
        content_hash: str,
        assignment_source: str,
    ) -> None:
        analysis = self.session.execute(
            select(ArticleAnalysisORM).where(ArticleAnalysisORM.article_id == article.id)
        ).scalar_one_or_none()
        if analysis is None:
            analysis = ArticleAnalysisORM(article_id=article.id)
            self.session.add(analysis)
        analysis.article_type = payload.article_type
        analysis.article_type_confidence = payload.article_type_confidence
        analysis.is_event_coverage = payload.is_event_coverage
        analysis.language = payload.language
        analysis.primary_topic_tag_id = (
            tag_by_code.get(payload.primary_tag_code) if payload.primary_tag_code else None
        )
        analysis.key_phrases_json = json.dumps(payload.key_phrases, ensure_ascii=False)
        analysis.claims_json = json.dumps(payload.claims, ensure_ascii=False)
        analysis.extraction_version = "v1"
        analysis.content_hash = content_hash
        self.session.flush()

        self.session.execute(delete(ArticleTagORM).where(ArticleTagORM.article_id == article.id))
        all_tag_codes = [
            code for code in [payload.primary_tag_code, *payload.secondary_tag_codes] if code
        ]
        for idx, code in enumerate(all_tag_codes):
            self.session.add(
                ArticleTagORM(
                    article_id=article.id,
                    tag_id=tag_by_code[code],
                    assignment_source=assignment_source,
                    confidence=payload.article_type_confidence,
                    is_primary=idx == 0,
                )
            )

        self.session.execute(
            delete(EntityMentionORM).where(EntityMentionORM.article_id == article.id)
        )
        merged_mentions: dict[tuple[int, int, str], dict[str, int | float | str | None]] = {}
        for entity_payload in payload.entities[:12]:
            entity_id = self._ensure_entity(entity_payload)
            mention = build_entity_mention(
                article=article,
                entity_id=entity_id,
                entity_payload=entity_payload,
            )
            mention_key = (
                mention["article_id"],
                mention["entity_id"],
                mention["mention_text_normalized"],
            )
            merged = merged_mentions.get(mention_key)
            if merged is None:
                merged_mentions[mention_key] = mention
                continue
            merged["mention_count"] += mention["mention_count"]
            merged["title_hits"] += mention["title_hits"]
            merged["summary_hits"] += mention["summary_hits"]
            merged["body_hits"] += mention["body_hits"]
            merged["relevance_score"] = max(merged["relevance_score"], mention["relevance_score"])
            if not merged["role_hint"] and mention["role_hint"]:
                merged["role_hint"] = mention["role_hint"]
            if len(mention["surface_form"]) > len(merged["surface_form"]):
                merged["surface_form"] = mention["surface_form"]

        for mention in merged_mentions.values():
            self.session.add(EntityMentionORM(**mention))

    def _ensure_entity(self, entity_payload: ArticleAnalysisExtractedEntity) -> int:
        canonical = self.canonicalizer.canonicalize(entity_payload)
        entity_row = self.session.execute(
            select(EntityORM).where(
                EntityORM.entity_type == canonical.entity_type,
                EntityORM.normalized_name == canonical.normalized_name,
            )
        ).scalar_one_or_none()
        if entity_row is None:
            entity_row = EntityORM(
                entity_type=canonical.entity_type,
                canonical_name=canonical.canonical_name,
                normalized_name=canonical.normalized_name,
                slug=canonical.slug,
                canonical_source=canonical.canonical_source,
            )
            self.session.add(entity_row)
            self.session.flush()

        aliases = {
            alias.normalized_alias
            for alias in self.session.execute(
                select(EntityAliasORM).where(EntityAliasORM.entity_id == entity_row.id)
            ).scalars()
        }
        for alias in canonical.aliases + (entity_payload.canonical_name,):
            normalized_alias = normalize_lookup(alias)
            if not normalized_alias or normalized_alias in aliases:
                continue
            self.session.add(
                EntityAliasORM(
                    entity_id=entity_row.id,
                    alias=alias,
                    normalized_alias=normalized_alias,
                    alias_type="surface",
                )
            )
            aliases.add(normalized_alias)
        return entity_row.id


def build_entity_mention(
    *,
    article: ArticleRead,
    entity_id: int,
    entity_payload: ArticleAnalysisExtractedEntity,
) -> dict[str, int | float | str | None]:
    surface = entity_payload.canonical_name.strip()
    article_title = article.title.lower()
    article_summary = article.summary.lower()
    article_body = article.article_text.lower()
    combined_text = " ".join([article.title, article.summary, article.article_text]).lower()
    return {
        "article_id": article.id,
        "entity_id": entity_id,
        "surface_form": surface,
        "mention_text_normalized": normalize_lookup(surface),
        "mention_count": combined_text.count(surface.lower()) or 1,
        "title_hits": article_title.count(surface.lower()),
        "summary_hits": article_summary.count(surface.lower()),
        "body_hits": article_body.count(surface.lower()),
        "relevance_score": entity_payload.relevance_score,
        "role_hint": entity_payload.role_hint,
    }
