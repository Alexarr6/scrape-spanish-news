from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace

import pytest

from src.semantic.contracts import EmbeddingArtifact, SemanticArticle
from src.semantic.dbstore import (
    MIN_TEXT_LENGTH,
    ExplorerFilters,
    SemanticWindow,
    _load_story_cluster_memberships,
    assemble_article_text,
    content_hash_for_text,
    embedding_dimensions_for_model,
    get_embedding_vector_dimensions,
    init_pgvector_schema,
    load_explorer_article_detail,
    load_explorer_points_page,
    load_neighbors_for_articles,
    load_projected_points,
    parse_vector_text,
    projection_kind_for_set,
    render_init_sql,
    resolve_semantic_window,
    select_cluster_aware_article_ids,
    select_embedding_candidates,
    select_source_balanced_article_ids,
    summary_snippet,
    upsert_embeddings,
    vector_literal,
)


def _article(**overrides) -> SemanticArticle:
    payload = {
        "article_id": 1,
        "source": "elpais",
        "title": "Titular",
        "url": "https://example.com/1",
        "published_at": "2026-03-17T00:00:00+00:00",
        "section": "espana",
        "summary": "Resumen corto",
        "article_text": "Texto largo del articulo con bastante contenido para pasar el minimo.",
    }
    payload.update(overrides)
    return SemanticArticle(**payload)


@dataclass
class _Row:
    id: int
    source: str = "elpais"
    title: str = "Titular"
    url: str = "https://example.com/1"
    published_at: object = None
    section: str = "espana"
    summary: str = "Resumen corto"
    article_text: str = "Texto largo del articulo con bastante contenido para pasar el minimo."


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self.filters = []
        self.params_seen = []

    def filter(self, *args, **_kwargs):
        self.filters.extend(args)
        return self

    def params(self, **kwargs):
        self.params_seen.append(kwargs)
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, _value):
        return self

    def all(self):
        return self._rows


class _ExistingResult:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def mappings(self):
        return self

    def first(self):
        return self._row

    def all(self):
        return self._rows


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value


class _SelectSession:
    def __init__(self, rows, existing_by_article_id, story_member_ids=None):
        self._rows = rows
        self._existing_by_article_id = existing_by_article_id
        self._story_member_ids = set(story_member_ids or [])
        self.last_query = None

    def query(self, _model):
        self.last_query = _FakeQuery(self._rows)
        return self.last_query

    def execute(self, statement, params=None):
        sql = str(statement)
        if "FROM story_clusters sc" in sql:
            article_ids = set((params or {}).values())
            rows = [
                {
                    "cluster_id": 1,
                    "article_count": len(self._story_member_ids),
                    "article_id": article_id,
                }
                for article_id in sorted(self._story_member_ids)
                if article_id in article_ids
            ]
            return _ExistingResult(rows=rows)
        if "FROM cluster_members" in sql:
            rows = [
                {"article_id": article_id}
                for article_id in self._story_member_ids
                if article_id in set((params or {}).values())
            ]
            return _ExistingResult(rows=rows)
        return _ExistingResult(self._existing_by_article_id.get(params["article_id"]))


class _UpsertSession:
    def __init__(self, schema_dim):
        self.schema_dim = schema_dim
        self.executed = []
        self.committed = False

    def connection(self):
        return self

    def execute(self, statement, params=None):
        sql = str(statement)
        if "format_type(a.atttypid, a.atttypmod) AS vector_type" in sql:
            return _ScalarResult(f"vector({self.schema_dim})")
        self.executed.append((sql, params))
        return SimpleNamespace()

    def commit(self):
        self.committed = True


class _NeighborSession:
    def __init__(self, rows_by_article_id):
        self.rows_by_article_id = rows_by_article_id

    def execute(self, _statement, params=None):
        rows = self.rows_by_article_id[params["article_id"]]
        return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: rows))


class _ExplorerQueryResult:
    def __init__(self, *, rows=None, first_row=None, scalar=None):
        self._rows = rows or []
        self._first_row = first_row
        self._scalar = scalar

    def mappings(self):
        return self

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._first_row

    def scalar_one(self):
        return self._scalar


class _SchemaResult:
    def __init__(self, *, scalar=None, scalar_or_none=None):
        self._scalar = scalar
        self._scalar_or_none = scalar_or_none

    def scalar_one(self):
        return self._scalar

    def scalar_one_or_none(self):
        return self._scalar_or_none


class _SchemaConn:
    def __init__(self, *, current_dim, row_count=0):
        self.current_dim = current_dim
        self.row_count = row_count
        self.executed_sql = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.executed_sql.append((sql, params))
        if "format_type(a.atttypid, a.atttypmod) AS vector_type" in sql:
            value = None if self.current_dim is None else f"vector({self.current_dim})"
            return _SchemaResult(scalar_or_none=value)
        if "SELECT COUNT(*) FROM article_embeddings" in sql:
            return _SchemaResult(scalar=self.row_count)
        return SimpleNamespace()


class _SchemaBegin:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


class _SchemaEngine:
    def __init__(self, conn):
        self.conn = conn

    def begin(self):
        return _SchemaBegin(self.conn)


class _ExplorerSession:
    def __init__(self):
        self.sql = []
        self.params = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.sql.append(sql)
        self.params.append(params or {})
        if "SELECT COUNT(*)" in sql:
            return _ExplorerQueryResult(scalar=0)
        if "SELECT article_id, cluster_id" in sql and "FROM cluster_members" in sql:
            return _ExplorerQueryResult(rows=[])
        if "FROM article_projections p" in sql:
            return _ExplorerQueryResult(rows=[])
        if "FROM articles a" in sql and "WHERE a.id = :article_id" in sql:
            return _ExplorerQueryResult(first_row=None)
        if "SELECT MIN(x) AS min_x" in sql:
            return _ExplorerQueryResult(
                first_row={
                    "min_x": None,
                    "max_x": None,
                    "min_y": None,
                    "max_y": None,
                    "min_z": None,
                    "max_z": None,
                }
            )
        if "SELECT DISTINCT" in sql:
            return _ExplorerQueryResult(rows=[])
        if "FROM semantic_clusters" in sql and "ORDER BY cluster_id ASC" in sql:
            return _ExplorerQueryResult(rows=[])
        if "FROM semantic_clusters" in sql and "ORDER BY size DESC" in sql:
            return _ExplorerQueryResult(rows=[])
        raise AssertionError(f"Unexpected SQL: {sql}")


def test_assemble_article_text_includes_source_and_section_context() -> None:
    text_value = assemble_article_text(_article(), max_chars=500)
    assert text_value.startswith("elpais | espana")
    assert "Titular" in text_value


def test_summary_snippet_falls_back_to_article_text() -> None:
    snippet = summary_snippet(_article(summary="", article_text="abc" * 120))
    assert snippet.startswith("abcabc")
    assert len(snippet) <= 240


def test_content_hash_is_stable_for_identical_text() -> None:
    text_value = assemble_article_text(_article(), max_chars=500)
    assert content_hash_for_text(text_value) == content_hash_for_text(text_value)


def test_vector_literal_round_trips_with_parser() -> None:
    assert parse_vector_text(vector_literal([0.1, -2.5, 3.0])) == [0.1, -2.5, 3.0]


def test_assembled_text_exceeds_minimum_threshold_for_valid_article() -> None:
    assert len(assemble_article_text(_article(), max_chars=500)) > MIN_TEXT_LENGTH


def test_embedding_dimensions_for_supported_models() -> None:
    assert embedding_dimensions_for_model("text-embedding-3-small") == 1536
    assert embedding_dimensions_for_model("text-embedding-3-large") == 3072


def test_render_init_sql_includes_semantic_analysis_tables() -> None:
    sql = render_init_sql(embedding_model="text-embedding-3-large")
    assert "embedding VECTOR(3072) NOT NULL" in sql
    assert "CREATE TABLE IF NOT EXISTS semantic_point_analysis" in sql
    assert "CREATE TABLE IF NOT EXISTS semantic_clusters" in sql


def test_get_embedding_vector_dimensions_parses_pgvector_type() -> None:
    bind = SimpleNamespace(execute=lambda *_args, **_kwargs: _ScalarResult("vector(3072)"))
    assert get_embedding_vector_dimensions(bind) == 3072


def test_select_embedding_candidates_skips_only_when_requested_model_matches() -> None:
    row = _Row(id=1)
    assembled_text = assemble_article_text(_article(), max_chars=500)
    content_hash = content_hash_for_text(assembled_text)
    session = _SelectSession(
        [row],
        existing_by_article_id={
            1: {"content_hash": content_hash, "embedding_model": "text-embedding-3-small"}
        },
    )
    candidates = select_embedding_candidates(
        session, limit=10, max_chars=500, embedding_model="text-embedding-3-large"
    )
    assert [candidate.article.article_id for candidate in candidates] == [1]


def test_upsert_embeddings_rejects_schema_dimension_mismatch() -> None:
    session = _UpsertSession(schema_dim=1536)
    record = EmbeddingArtifact(
        article_id=1,
        source="elpais",
        title="Titular",
        url="https://example.com/1",
        published_at="",
        section="espana",
        summary_snippet="Resumen corto",
        text_length=50,
        embedding_model="text-embedding-3-large",
        embedding=[0.0] * 3072,
    )
    with pytest.raises(RuntimeError, match=r"VECTOR\(1536\).*3072 dimensions"):
        upsert_embeddings(session, [record], content_hashes={1: "hash"}, source_text_chars={1: 50})


def test_init_pgvector_schema_reinit_executes_additive_semantic_schema_sql() -> None:
    conn = _SchemaConn(current_dim=1536)
    engine = _SchemaEngine(conn)

    init_pgvector_schema(engine, embedding_model="text-embedding-3-small")

    executed_sql = "\n".join(sql for sql, _params in conn.executed_sql)
    assert "CREATE TABLE IF NOT EXISTS semantic_point_analysis" in executed_sql
    assert "CREATE TABLE IF NOT EXISTS semantic_clusters" in executed_sql
    assert "CREATE INDEX IF NOT EXISTS ix_semantic_point_analysis_cluster_id" in executed_sql
    assert "CREATE INDEX IF NOT EXISTS ix_semantic_clusters_projection_set" in executed_sql
    assert (
        "ALTER TABLE article_embeddings ALTER COLUMN embedding TYPE VECTOR(1536)"
        not in executed_sql
    )


def test_init_pgvector_schema_preserves_dimension_mismatch_protection_on_reinit() -> None:
    conn = _SchemaConn(current_dim=1536, row_count=2)
    engine = _SchemaEngine(conn)

    with pytest.raises(RuntimeError, match=r"VECTOR\(1536\).*requires VECTOR\(3072\)"):
        init_pgvector_schema(engine, embedding_model="text-embedding-3-large")

    executed_sql = "\n".join(sql for sql, _params in conn.executed_sql)
    assert "CREATE TABLE IF NOT EXISTS semantic_point_analysis" not in executed_sql
    assert "CREATE TABLE IF NOT EXISTS semantic_clusters" not in executed_sql


def test_load_neighbors_for_articles_returns_enriched_neighbor_artifacts() -> None:
    session = _NeighborSession(
        {
            1: [
                {
                    "article_id": 2,
                    "similarity": 0.91,
                    "source": "elmundo",
                    "title": "Vecino",
                    "url": "https://example.com/2",
                    "published_at": "2026-03-17T00:00:00+00:00",
                    "published_date": "2026-03-17",
                    "display_date": "2026-03-17",
                    "section": "politica",
                    "summary_snippet": "resumen vecino",
                }
            ]
        }
    )
    payload = load_neighbors_for_articles(session, article_ids=[1], limit=3)
    assert payload[1][0].article_id == 2
    assert payload[1][0].similarity == pytest.approx(0.91)


def test_load_explorer_points_page_joins_semantic_analysis_when_filters_need_it() -> None:
    session = _ExplorerSession()
    load_explorer_points_page(session, filters=ExplorerFilters(cluster_id=2, outlier_only=True))
    joined_sql = "\n".join(session.sql)
    assert "LEFT JOIN semantic_point_analysis spa" in joined_sql
    assert "spa.cluster_id = :cluster_id" in joined_sql
    assert "spa.is_outlier = :outlier_only" in joined_sql


def test_load_explorer_points_page_filters_by_story_cluster_membership() -> None:
    session = _ExplorerSession()
    load_explorer_points_page(
        session,
        filters=ExplorerFilters(story_cluster_id=17, visual_mode="filter"),
    )
    joined_sql = "\n".join(session.sql)
    assert "FROM cluster_members cm" in joined_sql
    assert "cm.article_id = p.article_id" in joined_sql
    assert "cm.cluster_id = :story_cluster_id" in joined_sql


def test_load_explorer_points_page_keeps_broader_dataset_for_story_cluster_highlight() -> None:
    session = _ExplorerSession()
    load_explorer_points_page(
        session,
        filters=ExplorerFilters(story_cluster_id=17, visual_mode="highlight"),
    )
    joined_sql = "\n".join(session.sql)
    assert ":story_cluster_id" in joined_sql or any(
        params.get("story_cluster_id") == 17 for params in session.params
    )
    assert "EXISTS (SELECT 1 FROM cluster_members cm WHERE cm.article_id = p.article_id AND cm.cluster_id = :story_cluster_id)" not in joined_sql


def test_load_explorer_points_page_filters_search_only_in_filter_mode() -> None:
    session = _ExplorerSession()
    load_explorer_points_page(
        session,
        filters=ExplorerFilters(search="gobierno", visual_mode="filter"),
    )
    joined_sql = "\n".join(session.sql)
    assert "lower(a.title) LIKE :search OR lower(a.summary) LIKE :search" in joined_sql
    assert any(params.get("search") == "%gobierno%" for params in session.params)


def test_load_explorer_points_page_skips_search_where_clause_in_highlight_mode() -> None:
    session = _ExplorerSession()
    load_explorer_points_page(
        session,
        filters=ExplorerFilters(search="gobierno", visual_mode="highlight"),
    )
    joined_sql = "\n".join(session.sql)
    assert "lower(a.title) LIKE :search OR lower(a.summary) LIKE :search" not in joined_sql
    assert any(params.get("search") == "%gobierno%" for params in session.params)


def test_load_explorer_article_detail_formats_published_at_as_text_sql() -> None:
    session = _ExplorerSession()
    load_explorer_article_detail(session, article_id=1, projection_set="pca_2d_latest")
    sql = next(sql for sql in session.sql if "FROM articles a" in sql)
    assert "to_char(a.published_at AT TIME ZONE" in sql or "CAST(a.published_at AS TEXT)" in sql


def test_resolve_semantic_window_supports_days_back_and_explicit_dates() -> None:
    assert resolve_semantic_window(days_back=3, today=date(2026, 3, 18)) == SemanticWindow(
        date_from="2026-03-16",
        date_to="2026-03-18",
    )
    assert resolve_semantic_window(date_from="2026-03-01", date_to="2026-03-05") == SemanticWindow(
        date_from="2026-03-01",
        date_to="2026-03-05",
    )


def test_resolve_semantic_window_rejects_invalid_combinations() -> None:
    with pytest.raises(ValueError, match="cannot be combined"):
        resolve_semantic_window(days_back=2, date_from="2026-03-01")
    with pytest.raises(ValueError, match="cannot be after"):
        resolve_semantic_window(date_from="2026-03-05", date_to="2026-03-01")


def test_select_embedding_candidates_applies_window_filters() -> None:
    row = _Row(id=1)
    session = _SelectSession([row], existing_by_article_id={})

    candidates = select_embedding_candidates(
        session,
        limit=10,
        max_chars=500,
        window=SemanticWindow(date_from="2026-03-10", date_to="2026-03-12"),
    )

    assert [candidate.article.article_id for candidate in candidates] == [1]
    assert any("window_date_from" in params for params in session.last_query.params_seen)
    assert any("window_date_to" in params for params in session.last_query.params_seen)


def test_select_embedding_candidates_uses_source_balanced_round_robin() -> None:
    rows = [
        _Row(id=1, source="elpais"),
        _Row(id=2, source="elpais"),
        _Row(id=3, source="elpais"),
        _Row(id=4, source="elmundo"),
        _Row(id=5, source="eldiario"),
    ]
    session = _SelectSession(rows, existing_by_article_id={})

    candidates = select_embedding_candidates(session, limit=4, max_chars=500)

    assert [candidate.article.article_id for candidate in candidates] == [1, 4, 5, 2]


def test_select_embedding_candidates_prioritizes_story_members_before_plain_recency() -> None:
    rows = [
        _Row(id=1, source="elpais"),
        _Row(id=2, source="elpais"),
        _Row(id=3, source="elmundo"),
        _Row(id=4, source="eldiario"),
    ]
    session = _SelectSession(rows, existing_by_article_id={}, story_member_ids={2, 3})

    candidates = select_embedding_candidates(
        session,
        limit=4,
        max_chars=500,
        prioritize_story_members=True,
    )

    assert [candidate.article.article_id for candidate in candidates] == [2, 3, 1, 4]


def test_select_cluster_aware_article_ids_keeps_complete_qualifying_clusters_together() -> None:
    records = [
        _article(article_id=10, source="elpais"),
        _article(article_id=11, source="elmundo"),
        _article(article_id=20, source="abc"),
        _article(article_id=21, source="abc"),
        _article(article_id=30, source="eldiario"),
    ]

    article_ids = select_cluster_aware_article_ids(
        records,
        limit=4,
        priority_groups=[
            SimpleNamespace(cluster_id=7, article_count=2, article_ids=[20, 21]),
            SimpleNamespace(cluster_id=8, article_count=2, article_ids=[10, 11]),
        ],
    )

    assert article_ids == [20, 21, 10, 11]


def test_select_cluster_aware_article_ids_skips_partial_cluster_that_would_bust_limit() -> None:
    records = [
        _article(article_id=1, source="elpais"),
        _article(article_id=2, source="elmundo"),
        _article(article_id=3, source="abc"),
        _article(article_id=4, source="eldiario"),
    ]

    article_ids = select_cluster_aware_article_ids(
        records,
        limit=3,
        priority_groups=[
            SimpleNamespace(cluster_id=9, article_count=2, article_ids=[1, 2]),
            SimpleNamespace(cluster_id=10, article_count=2, article_ids=[3, 4]),
        ],
    )

    assert article_ids == [1, 2, 3]


def test_select_cluster_aware_article_ids_singletons_do_not_preempt_qualifying_clusters() -> None:
    records = [
        _article(article_id=1, source="elpais"),
        _article(article_id=2, source="elpais"),
        _article(article_id=3, source="elmundo"),
        _article(article_id=4, source="eldiario"),
    ]

    article_ids = select_cluster_aware_article_ids(
        records,
        limit=3,
        priority_groups=[SimpleNamespace(cluster_id=5, article_count=2, article_ids=[2, 3])],
    )

    assert article_ids[:2] == [2, 3]


def test_select_source_balanced_article_ids_round_robins_sources() -> None:
    records = [
        _article(article_id=1, source="elpais"),
        _article(article_id=2, source="elpais"),
        _article(article_id=3, source="elmundo"),
        _article(article_id=4, source="eldiario"),
        _article(article_id=5, source="eldiario"),
    ]

    assert select_source_balanced_article_ids(records, limit=4) == [1, 3, 4, 2]


def test_load_projected_points_applies_window_filters_to_sql() -> None:
    session = _ExplorerSession()

    load_projected_points(
        session,
        projection_set="pca_3d_latest",
        window=SemanticWindow(date_from="2026-03-10", date_to="2026-03-12"),
    )

    sql = next(
        sql
        for sql in session.sql
        if "FROM article_projections p" in sql and "LIMIT :limit" not in sql
    )
    assert "date(a.published_at) >= date(:window_date_from)" in sql
    assert "date(a.published_at) <= date(:window_date_to)" in sql
    params = next(
        params for params in session.params if params.get("projection_set") == "pca_3d_latest"
    )
    assert params["window_date_from"] == "2026-03-10"
    assert params["window_date_to"] == "2026-03-12"


def test_projection_kind_for_set_distinguishes_2d_and_3d_sets() -> None:
    assert projection_kind_for_set("pca_2d_latest") == "pca_2d"
    assert projection_kind_for_set("pca_3d_latest") == "pca_3d"


# ---------------------------------------------------------------------------
# _load_story_cluster_memberships — unit tests
# ---------------------------------------------------------------------------


def _make_membership_row(article_id: int, cluster_id: int) -> dict:
    return {"article_id": article_id, "cluster_id": cluster_id}


class _MembershipSession:
    """Minimal session stub for _load_story_cluster_memberships tests."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def execute(self, _statement, _params=None):
        return SimpleNamespace(
            mappings=lambda: SimpleNamespace(all=lambda: self._rows)
        )


def test_load_story_cluster_memberships_returns_cluster_ids_per_article() -> None:
    rows = [
        _make_membership_row(article_id=10, cluster_id=501),
        _make_membership_row(article_id=20, cluster_id=502),
        _make_membership_row(article_id=20, cluster_id=503),
    ]
    session = _MembershipSession(rows)
    result = _load_story_cluster_memberships(session, article_ids=[10, 20, 30])
    assert result[10] == [501]
    assert result[20] == [502, 503]
    assert result[30] == []  # pre-seeded empty list for articles without memberships


def test_load_story_cluster_memberships_returns_empty_dict_for_no_article_ids() -> None:
    session = _MembershipSession([])
    assert _load_story_cluster_memberships(session, article_ids=[]) == {}


def test_load_story_cluster_memberships_handles_article_with_no_memberships() -> None:
    session = _MembershipSession([])  # DB returns nothing
    result = _load_story_cluster_memberships(session, article_ids=[1, 2])
    assert result == {1: [], 2: []}


# ---------------------------------------------------------------------------
# load_explorer_points_page — story_cluster_ids payload wiring tests
# ---------------------------------------------------------------------------


def _make_point_row(**overrides) -> dict:
    """Return a minimal synthetic row matching load_explorer_points_page expectations."""
    base: dict = {
        "article_id": 1,
        "source": "elpais",
        "title": "Test",
        "url": "https://example.com/1",
        "published_at": "2026-03-17T00:00:00+00:00",
        "published_date": "2026-03-17",
        "display_date": "2026-03-17",
        "section": "politica",
        "summary_snippet": "resumen",
        "x": 0.5,
        "y": -0.3,
        "z": 0.1,
        "cluster_id": None,
        "cluster_size": 0,
        "is_outlier": False,
        "local_density_distance": 0.0,
        "source_neighbor_diversity": 0,
        "nearby_sources_json": "[]",
    }
    base.update(overrides)
    return base


class _ExplorerSessionWithRows(_ExplorerSession):
    """Explorer session stub that returns configurable point rows and membership data."""

    def __init__(
        self,
        *,
        point_rows: list[dict] | None = None,
        membership_rows: list[dict] | None = None,
    ) -> None:
        super().__init__()
        self._point_rows = point_rows or []
        self._membership_rows = membership_rows or []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.sql.append(sql)
        self.params.append(params or {})
        if "SELECT COUNT(*)" in sql:
            return _ExplorerQueryResult(scalar=len(self._point_rows))
        if "SELECT article_id, cluster_id" in sql and "FROM cluster_members" in sql:
            return _ExplorerQueryResult(rows=self._membership_rows)
        if "FROM article_projections p" in sql and "LIMIT :limit" in sql:
            return _ExplorerQueryResult(rows=self._point_rows)
        # nearest_neighbors is called inside _safe_neighbors; swallow via parent
        if "FROM article_embeddings seed" in sql:
            return _ExplorerQueryResult(rows=[])
        return super().execute(statement, params)


def test_load_explorer_points_page_populates_story_cluster_ids_in_highlight_mode() -> None:
    """story_cluster_ids must appear on returned items even in highlight (non-filter) mode."""
    point_rows = [
        _make_point_row(article_id=1),
        _make_point_row(article_id=2, source="elmundo"),
    ]
    membership_rows = [
        {"article_id": 1, "cluster_id": 501},
        {"article_id": 2, "cluster_id": 502},
    ]
    session = _ExplorerSessionWithRows(
        point_rows=point_rows,
        membership_rows=membership_rows,
    )
    page = load_explorer_points_page(
        session,
        filters=ExplorerFilters(story_cluster_id=502, visual_mode="highlight"),
    )
    assert page.story_cluster_metadata_available is True
    by_article_id = {item.article_id: item.analysis.story_cluster_ids for item in page.items}
    assert by_article_id[1] == [501], "article 1 must carry its story cluster even though it is not the highlighted cluster"
    assert by_article_id[2] == [502], "article 2 must carry its own story cluster"


def test_load_explorer_points_page_story_cluster_ids_empty_for_unaffiliated_points() -> None:
    """Points with no cluster_members rows must get an empty story_cluster_ids list."""
    point_rows = [_make_point_row(article_id=99, source="abc")]
    session = _ExplorerSessionWithRows(point_rows=point_rows, membership_rows=[])
    page = load_explorer_points_page(session, filters=ExplorerFilters())
    assert page.items[0].analysis.story_cluster_ids == []


def test_load_explorer_points_page_story_cluster_ids_deduplicated_and_sorted() -> None:
    """story_cluster_ids must be sorted and deduplicated (defensive check on _analysis_for_row)."""
    point_rows = [_make_point_row(article_id=5)]
    membership_rows = [
        {"article_id": 5, "cluster_id": 300},
        {"article_id": 5, "cluster_id": 100},
        {"article_id": 5, "cluster_id": 300},
    ]
    session = _ExplorerSessionWithRows(point_rows=point_rows, membership_rows=membership_rows)
    page = load_explorer_points_page(session, filters=ExplorerFilters())
    assert page.items[0].analysis.story_cluster_ids == [100, 300]
