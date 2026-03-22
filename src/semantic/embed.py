from __future__ import annotations

import os
from collections.abc import Iterable

from openai import OpenAI

from src.semantic.contracts import (
    EmbeddingArtifact,
    SemanticArticle,
    SemanticBuildConfig,
    SemanticMetrics,
)
from src.semantic.dbstore import assemble_article_text, summary_snippet


def build_embedding_artifacts(
    *,
    articles: list[SemanticArticle],
    config: SemanticBuildConfig,
    metrics: SemanticMetrics,
) -> list[EmbeddingArtifact]:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    eligible = [
        article
        for article in articles
        if assemble_article_text(article, max_chars=config.max_chars)
    ]
    metrics.eligible_rows = len(eligible)
    metrics.skipped_empty_text = len(articles) - len(eligible)
    metrics.embedding_model = config.embedding_model
    metrics.embedding_batch_size = config.batch_size

    records: list[EmbeddingArtifact] = []
    for batch in _chunked(eligible, config.batch_size):
        inputs = [assemble_article_text(article, max_chars=config.max_chars) for article in batch]
        response = client.embeddings.create(model=config.embedding_model, input=inputs)
        metrics.embedding_requests += 1
        for article, item in zip(batch, response.data, strict=True):
            vector = [float(x) for x in item.embedding]
            metrics.embedding_dimensions = len(vector)
            records.append(
                EmbeddingArtifact(
                    article_id=article.article_id,
                    source=article.source,
                    title=article.title,
                    url=article.url,
                    published_at=article.published_at,
                    section=article.section,
                    summary_snippet=summary_snippet(article),
                    text_length=len(assemble_article_text(article, max_chars=config.max_chars)),
                    embedding_model=config.embedding_model,
                    embedding=vector,
                )
            )
    return records


def _chunked(items: list[SemanticArticle], size: int) -> Iterable[list[SemanticArticle]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]
