from src.semantic.contracts import EmbeddingArtifact, NeighborArtifact, PointArtifact, SemanticArticle


def test_semantic_article_text_length_tracks_article_text() -> None:
    article = SemanticArticle(
        article_id=7,
        source="elpais",
        title="Titular",
        url="https://example.com/a",
        published_at="2026-03-17T00:00:00+00:00",
        section="espana",
        summary="Resumen",
        article_text="Texto largo",
    )

    assert article.text_length == len("Texto largo")


def test_artifact_model_dump_is_plain_dict() -> None:
    embedding = EmbeddingArtifact(
        article_id=1,
        source="abc",
        title="Hola",
        url="https://example.com/1",
        published_at="",
        section="",
        summary_snippet="resumen",
        text_length=9,
        embedding_model="text-embedding-3-small",
        embedding=[0.1, 0.2],
    )
    neighbor = NeighborArtifact(
        article_id=2,
        similarity=0.91,
        source="elpais",
        title="Vecino",
        url="https://example.com/2",
        published_at="2026-03-17T00:00:00+00:00",
        published_date="2026-03-17",
        display_date="2026-03-17",
        section="espana",
        summary_snippet="vecino cercano",
    )
    point = PointArtifact(
        article_id=1,
        source="abc",
        title="Hola",
        url="https://example.com/1",
        published_at="",
        published_date="2026-03-17",
        display_date="2026-03-17",
        section="",
        summary_snippet="resumen",
        text_length=9,
        embedding_model="text-embedding-3-small",
        x=1.0,
        y=-1.0,
        neighbors=[neighbor],
    )

    assert embedding.model_dump()["embedding"] == [0.1, 0.2]
    assert point.model_dump()["x"] == 1.0
    assert point.model_dump()["neighbors"][0]["article_id"] == 2
