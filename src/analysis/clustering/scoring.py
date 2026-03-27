from __future__ import annotations

from src.analysis.shared.contracts import StoryClusterMemberReason
from src.analysis.shared.heuristics import (
    event_terms,
    followup_markers,
    lexical_signature,
    title_similarity,
)
from src.analysis.shared.normalization import jaccard_similarity, normalize_lookup
from src.analysis.shared.types import EnrichedArticle


class StoryPairScorer:
    def score_pair(self, left: EnrichedArticle, right: EnrichedArticle) -> StoryClusterMemberReason:
        left_keyphrases = [
            normalize_lookup(value) for value in left.key_phrases if normalize_lookup(value)
        ]
        right_keyphrases = [
            normalize_lookup(value) for value in right.key_phrases if normalize_lookup(value)
        ]
        left_signature = lexical_signature(left.article.title, left.article.summary)
        right_signature = lexical_signature(right.article.title, right.article.summary)
        lexical_overlap_score = jaccard_similarity(left_signature, right_signature)
        left_event_terms = event_terms(
            f"{left.article.title} {left.article.summary} {' '.join(left.key_phrases)}"
        )
        right_event_terms = event_terms(
            f"{right.article.title} {right.article.summary} {' '.join(right.key_phrases)}"
        )
        event_overlap_score = jaccard_similarity(left_event_terms, right_event_terms)
        left_followup_terms = followup_markers(f"{left.article.title} {left.article.summary}")
        right_followup_terms = followup_markers(f"{right.article.title} {right.article.summary}")
        followup_marker_overlap = jaccard_similarity(left_followup_terms, right_followup_terms)
        semantic_similarity = max(
            jaccard_similarity(
                left_keyphrases + left.entity_slugs,
                right_keyphrases + right.entity_slugs,
            ),
            round((lexical_overlap_score * 0.6) + (event_overlap_score * 0.4), 4),
        )
        title_sim = title_similarity(left.article.title, right.article.title)
        lede_sim = title_similarity(
            f"{left.article.title}. {left.article.summary}".strip(),
            f"{right.article.title}. {right.article.summary}".strip(),
        )
        shared_entity_score = jaccard_similarity(left.entity_slugs, right.entity_slugs)
        entity_salience_score = min(
            1.0,
            shared_entity_score
            * (1.0 if len(set(left.entity_slugs) & set(right.entity_slugs)) >= 2 else 0.72),
        )
        tag_overlap_score = jaccard_similarity(left.tag_codes, right.tag_codes)
        keyphrase_overlap_score = max(
            jaccard_similarity(left_keyphrases, right_keyphrases),
            lexical_overlap_score,
        )
        shared_entities = sorted(set(left.entity_slugs) & set(right.entity_slugs))
        shared_keyphrases = sorted(set(left_keyphrases) & set(right_keyphrases))
        shared_tags = sorted(set(left.tag_codes) & set(right.tag_codes))
        days_delta = abs((left.article.published_at - right.article.published_at).days)
        temporal_proximity_score = max(0.0, 1 - (days_delta / 7))
        penalties: list[str] = []
        hard_block = None
        secondary_types = {"analysis", "explainer", "feature", "interview"}
        article_types = {left.analysis.article_type, right.analysis.article_type}
        article_type_pair_class = (
            "secondary_form_pair" if article_types & secondary_types else "primary_pair"
        )
        risky_bridge_pair = False
        has_followup_shape = (
            days_delta <= 4
            and shared_entity_score >= 0.5
            and (
                event_overlap_score >= 0.14
                or lexical_overlap_score >= 0.18
                or followup_marker_overlap > 0
                or (len(shared_entities) >= 2 and tag_overlap_score >= 0.33)
            )
        )
        is_recurring_results_pair = self.is_recurring_results_article(
            left
        ) and self.is_recurring_results_article(right)
        same_results_game = self.results_game_key(left) == self.results_game_key(right)
        is_schedule_series_pair = self.is_schedule_series_article(
            left
        ) and self.is_schedule_series_article(right)
        is_question_utility_pair = self.is_question_utility_article(
            left
        ) and self.is_question_utility_article(right)
        is_live_blog_pair = self.is_live_blog_article(left) or self.is_live_blog_article(right)
        clean_followup_continuity = (
            days_delta <= 4
            and len(shared_entities) >= 2
            and (
                len(shared_tags) >= 1
                or len(shared_keyphrases) >= 1
                or followup_marker_overlap > 0
                or event_overlap_score >= 0.14
            )
        )
        clean_rewrite_shape = (
            days_delta <= 3
            and title_sim >= 0.74
            and lexical_overlap_score >= 0.22
            and (
                len(shared_entities) >= 1
                or len(shared_tags) >= 1
                or len(shared_keyphrases) >= 1
            )
        )
        cross_source_clean_rewrite = (
            left.article.source != right.article.source
            and days_delta <= 3
            and title_sim >= 0.7
            and lexical_overlap_score >= 0.2
            and (
                len(shared_entities) >= 1
                or len(shared_tags) >= 1
                or len(shared_keyphrases) >= 1
            )
        )
        event_continuity_score = min(
            1.0,
            (
                (0.45 if len(shared_entities) >= 2 else 0.0)
                + (0.2 if tag_overlap_score >= 0.33 else 0.0)
                + (0.2 if event_overlap_score >= 0.14 else 0.0)
                + (0.15 if followup_marker_overlap > 0 else 0.0)
            ),
        )
        if article_types & {"opinion", "editorial"}:
            if (
                left.analysis.article_type != right.analysis.article_type
                or article_types != {"opinion"}
            ):
                hard_block = "opinion_editorial_excluded_from_primary_clusters"
        if (
            hard_block is None
            and is_recurring_results_pair
            and (
                left.article.published_at.date() != right.article.published_at.date()
                or not same_results_game
            )
        ):
            hard_block = "recurring_results_series_excluded"
        if (
            hard_block is None
            and is_question_utility_pair
            and left.article.source == right.article.source
            and max(title_sim, lede_sim) < 0.9
        ):
            hard_block = "question_utility_series_excluded"
        if (
            hard_block is None
            and is_schedule_series_pair
            and left.article.source == right.article.source
            and (
                self.schedule_series_key(left) == self.schedule_series_key(right)
                and self.schedule_series_day_key(left) != self.schedule_series_day_key(right)
                or max(title_sim, lede_sim) < 0.96
            )
        ):
            hard_block = "schedule_series_excluded"
        if (
            hard_block is None
            and is_live_blog_pair
            and left.article.source == right.article.source
            and max(title_sim, lede_sim) < 0.9
        ):
            hard_block = "live_blog_series_excluded"
        if article_types & secondary_types and (lede_sim < 0.58 or keyphrase_overlap_score < 0.32):
            penalties.append("secondary_form_penalty")
            if (
                shared_entity_score >= 0.5
                and keyphrase_overlap_score < 0.24
                and event_overlap_score < 0.2
            ):
                risky_bridge_pair = True
                penalties.append("entity_glue_penalty")
        if (
            days_delta >= 2
            and not has_followup_shape
            and lede_sim < 0.56
            and keyphrase_overlap_score < 0.4
        ):
            penalties.append("followup_penalty")
        if (
            shared_entity_score >= 0.5
            and not has_followup_shape
            and (lede_sim < 0.6 or article_types & secondary_types)
            and keyphrase_overlap_score < 0.24
            and event_overlap_score < 0.2
            and tag_overlap_score < 0.75
        ):
            penalties.append("entity_glue_penalty")
            risky_bridge_pair = True
        if (
            days_delta >= 4
            and semantic_similarity < 0.52
            and lede_sim < 0.62
            and event_overlap_score < 0.2
        ):
            penalties.append("late_story_drift_penalty")
            risky_bridge_pair = True
        score = (
            semantic_similarity * 0.22
            + max(title_sim, lede_sim) * 0.16
            + lede_sim * 0.14
            + entity_salience_score * 0.16
            + tag_overlap_score * 0.07
            + keyphrase_overlap_score * 0.09
            + event_overlap_score * 0.04
            + event_continuity_score * 0.10
            + temporal_proximity_score * 0.02
        )
        if has_followup_shape:
            score += 0.06
        if clean_followup_continuity:
            score += 0.04
        if clean_rewrite_shape:
            score += 0.06
        if cross_source_clean_rewrite:
            score += 0.04
        if "secondary_form_penalty" in penalties:
            score -= 0.14
        if "followup_penalty" in penalties:
            score -= 0.12
        if "entity_glue_penalty" in penalties:
            score -= 0.14
        if "late_story_drift_penalty" in penalties:
            score -= 0.12
        return StoryClusterMemberReason(
            score=max(0.0, round(score, 4)),
            semantic_similarity=round(semantic_similarity, 4),
            title_similarity=round(max(title_sim, lede_sim), 4),
            shared_entity_score=round(entity_salience_score, 4),
            tag_overlap_score=round(tag_overlap_score, 4),
            keyphrase_overlap_score=round(keyphrase_overlap_score, 4),
            temporal_proximity_score=round(temporal_proximity_score, 4),
            days_delta=days_delta,
            shared_entity_count=len(shared_entities),
            shared_keyphrase_count=len(shared_keyphrases),
            shared_tag_count=len(shared_tags),
            article_type_pair_class=article_type_pair_class,
            risky_bridge_pair=risky_bridge_pair,
            hard_block=hard_block,
            penalties=penalties,
        )

    def is_recurring_results_article(self, article: EnrichedArticle) -> bool:
        title = normalize_lookup(article.article.title)
        summary = normalize_lookup(article.article.summary)
        text = " ".join(bit for bit in [title, summary] if bit)
        lottery_terms = {"bonoloto", "primitiva", "euromillones", "once"}
        return (
            "comprobar" in text
            and "resultados" in text
            and "hoy" in text
            and any(term in text for term in lottery_terms)
        )

    def results_game_key(self, article: EnrichedArticle) -> str:
        text = normalize_lookup(article.article.title)
        for game in ("bonoloto", "primitiva", "euromillones", "once"):
            if game in text:
                return game
        return ""

    def is_question_utility_article(self, article: EnrichedArticle) -> bool:
        title = article.article.title.strip().lower()
        summary = normalize_lookup(article.article.summary)
        question_markers = (
            "¿" in article.article.title or article.article.title.strip().endswith("?")
        )
        utility_markers = (
            "legálitas" in article.article.title.lower()
            or "legalitas" in title
            or "alquiler" in summary
            or "casero" in summary
            or "inquilino" in summary
            or "hipoteca" in summary
            or "vivienda" in summary
            or "local" in summary
        )
        return question_markers and utility_markers

    def is_schedule_series_article(self, article: EnrichedArticle) -> bool:
        text = normalize_lookup(article.article.title)
        return "itinerarios" in text and "horarios" in text and "semana santa" in text

    def is_live_blog_article(self, article: EnrichedArticle) -> bool:
        text = normalize_lookup(article.article.title)
        return (
            "ultima hora" in text
            or "última hora" in article.article.title.lower()
            or "en directo" in text
            or "minuto a minuto" in text
        )

    def schedule_series_key(self, article: EnrichedArticle) -> str:
        text = normalize_lookup(article.article.title)
        if "semana santa de cordoba" in text:
            return "semana_santa_cordoba"
        return ""

    def schedule_series_day_key(self, article: EnrichedArticle) -> str:
        text = normalize_lookup(article.article.title)
        for day in (
            "domingo de ramos",
            "lunes santo",
            "martes santo",
            "miercoles santo",
            "jueves santo",
            "madrugada",
            "viernes santo",
            "domingo de resurreccion",
        ):
            if day in text:
                return day
        return ""
