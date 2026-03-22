from src.semantic.contracts import (
    ClusterArtifact,
    EmbeddingArtifact,
    NeighborArtifact,
    PointAnalysisArtifact,
    PointArtifact,
    SemanticAnalysisArtifact,
    SemanticArticle,
)


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
        z=0.5,
        neighbors=[neighbor],
        analysis=PointAnalysisArtifact(
            article_id=1,
            cluster_id=4,
            cluster_size=8,
            is_outlier=False,
            local_density_distance=0.42,
            source_neighbor_diversity=3,
            nearby_sources=["abc", "elpais", "elmundo"],
        ),
    )

    analysis = SemanticAnalysisArtifact(
        points=[point.analysis],
        clusters=[
            ClusterArtifact(
                cluster_id=4,
                size=8,
                article_ids=[1, 2, 3],
                representative_article_ids=[1, 2],
                top_sources={"abc": 3, "elpais": 3, "elmundo": 2},
                source_count=3,
                source_dominance=0.375,
            )
        ],
        unclustered_article_ids=[9],
        density_baseline=0.5,
        outlier_count=1,
    )

    assert embedding.model_dump()["embedding"] == [0.1, 0.2]
    assert point.model_dump()["x"] == 1.0
    assert point.model_dump()["z"] == 0.5
    assert point.model_dump()["neighbors"][0]["article_id"] == 2
    assert point.model_dump()["analysis"]["cluster_id"] == 4
    assert analysis.model_dump()["clusters"][0]["top_sources"]["abc"] == 3
