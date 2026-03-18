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
    assemble_article_text,
    content_hash_for_text,
    embedding_dimensions_for_model,
    get_embedding_vector_dimensions,
    load_explorer_article_detail,
    load_explorer_points_page,
    load_neighbors_for_articles,
    load_projected_points,
    parse_vector_text,
    projection_kind_for_set,
    render_init_sql,
    resolve_semantic_window,
    select_embedding_candidates,
    summary_snippet,
    upsert_embeddings,
    vector_literal,
)


def _article(**overrides) -> SemanticArticle:
    payload = {
        'article_id': 1,
        'source': 'elpais',
        'title': 'Titular',
        'url': 'https://example.com/1',
        'published_at': '2026-03-17T00:00:00+00:00',
        'section': 'espana',
        'summary': 'Resumen corto',
        'article_text': 'Texto largo del articulo con bastante contenido para pasar el minimo.',
    }
    payload.update(overrides)
    return SemanticArticle(**payload)


@dataclass
class _Row:
    id: int
    source: str = 'elpais'
    title: str = 'Titular'
    url: str = 'https://example.com/1'
    published_at: object = None
    section: str = 'espana'
    summary: str = 'Resumen corto'
    article_text: str = 'Texto largo del articulo con bastante contenido para pasar el minimo.'


class _FakeQuery:
    def __init__(self, rows): self._rows = rows; self.filters = []; self.params_seen = []
    def filter(self, *args, **_kwargs): self.filters.extend(args); return self
    def params(self, **kwargs): self.params_seen.append(kwargs); return self
    def order_by(self, *_args, **_kwargs): return self
    def limit(self, _value): return self
    def all(self): return self._rows


class _ExistingResult:
    def __init__(self, row): self._row = row
    def mappings(self): return self
    def first(self): return self._row


class _ScalarResult:
    def __init__(self, value): self._value = value
    def scalar_one_or_none(self): return self._value
    def scalar_one(self): return self._value


class _SelectSession:
    def __init__(self, rows, existing_by_article_id): self._rows = rows; self._existing_by_article_id = existing_by_article_id; self.last_query = None
    def query(self, _model): self.last_query = _FakeQuery(self._rows); return self.last_query
    def execute(self, _statement, params=None): return _ExistingResult(self._existing_by_article_id.get(params['article_id']))


class _UpsertSession:
    def __init__(self, schema_dim): self.schema_dim = schema_dim; self.executed = []; self.committed = False
    def connection(self): return self
    def execute(self, statement, params=None):
        sql = str(statement)
        if 'format_type(a.atttypid, a.atttypmod) AS vector_type' in sql: return _ScalarResult(f'vector({self.schema_dim})')
        self.executed.append((sql, params)); return SimpleNamespace()
    def commit(self): self.committed = True


class _NeighborSession:
    def __init__(self, rows_by_article_id): self.rows_by_article_id = rows_by_article_id
    def execute(self, _statement, params=None):
        rows = self.rows_by_article_id[params['article_id']]
        return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: rows))


class _ExplorerQueryResult:
    def __init__(self, *, rows=None, first_row=None, scalar=None): self._rows = rows or []; self._first_row = first_row; self._scalar = scalar
    def mappings(self): return self
    def scalars(self): return self
    def all(self): return self._rows
    def first(self): return self._first_row
    def scalar_one(self): return self._scalar


class _ExplorerSession:
    def __init__(self): self.sql = []; self.params = []
    def execute(self, statement, params=None):
        sql = str(statement)
        self.sql.append(sql)
        self.params.append(params or {})
        if 'SELECT COUNT(*)' in sql: return _ExplorerQueryResult(scalar=0)
        if 'FROM article_projections p' in sql: return _ExplorerQueryResult(rows=[])
        if 'FROM articles a' in sql and 'WHERE a.id = :article_id' in sql: return _ExplorerQueryResult(first_row=None)
        if 'SELECT MIN(x) AS min_x' in sql: return _ExplorerQueryResult(first_row={'min_x': None, 'max_x': None, 'min_y': None, 'max_y': None, 'min_z': None, 'max_z': None})
        if 'SELECT DISTINCT' in sql: return _ExplorerQueryResult(rows=[])
        if 'FROM semantic_clusters' in sql and 'ORDER BY cluster_id ASC' in sql: return _ExplorerQueryResult(rows=[])
        if 'FROM semantic_clusters' in sql and 'ORDER BY size DESC' in sql: return _ExplorerQueryResult(rows=[])
        raise AssertionError(f'Unexpected SQL: {sql}')


def test_assemble_article_text_includes_source_and_section_context() -> None:
    text_value = assemble_article_text(_article(), max_chars=500)
    assert text_value.startswith('elpais | espana')
    assert 'Titular' in text_value


def test_summary_snippet_falls_back_to_article_text() -> None:
    snippet = summary_snippet(_article(summary='', article_text='abc' * 120))
    assert snippet.startswith('abcabc')
    assert len(snippet) <= 240


def test_content_hash_is_stable_for_identical_text() -> None:
    text_value = assemble_article_text(_article(), max_chars=500)
    assert content_hash_for_text(text_value) == content_hash_for_text(text_value)


def test_vector_literal_round_trips_with_parser() -> None:
    assert parse_vector_text(vector_literal([0.1, -2.5, 3.0])) == [0.1, -2.5, 3.0]


def test_assembled_text_exceeds_minimum_threshold_for_valid_article() -> None:
    assert len(assemble_article_text(_article(), max_chars=500)) > MIN_TEXT_LENGTH


def test_embedding_dimensions_for_supported_models() -> None:
    assert embedding_dimensions_for_model('text-embedding-3-small') == 1536
    assert embedding_dimensions_for_model('text-embedding-3-large') == 3072


def test_render_init_sql_includes_semantic_analysis_tables() -> None:
    sql = render_init_sql(embedding_model='text-embedding-3-large')
    assert 'embedding VECTOR(3072) NOT NULL' in sql
    assert 'CREATE TABLE IF NOT EXISTS semantic_point_analysis' in sql
    assert 'CREATE TABLE IF NOT EXISTS semantic_clusters' in sql


def test_get_embedding_vector_dimensions_parses_pgvector_type() -> None:
    bind = SimpleNamespace(execute=lambda *_args, **_kwargs: _ScalarResult('vector(3072)'))
    assert get_embedding_vector_dimensions(bind) == 3072


def test_select_embedding_candidates_skips_only_when_requested_model_matches() -> None:
    row = _Row(id=1)
    assembled_text = assemble_article_text(_article(), max_chars=500)
    content_hash = content_hash_for_text(assembled_text)
    session = _SelectSession([row], existing_by_article_id={1: {'content_hash': content_hash, 'embedding_model': 'text-embedding-3-small'}})
    candidates = select_embedding_candidates(session, limit=10, max_chars=500, embedding_model='text-embedding-3-large')
    assert [candidate.article.article_id for candidate in candidates] == [1]


def test_upsert_embeddings_rejects_schema_dimension_mismatch() -> None:
    session = _UpsertSession(schema_dim=1536)
    record = EmbeddingArtifact(article_id=1, source='elpais', title='Titular', url='https://example.com/1', published_at='', section='espana', summary_snippet='Resumen corto', text_length=50, embedding_model='text-embedding-3-large', embedding=[0.0] * 3072)
    with pytest.raises(RuntimeError, match=r'VECTOR\(1536\).*3072 dimensions'):
        upsert_embeddings(session, [record], content_hashes={1: 'hash'}, source_text_chars={1: 50})


def test_load_neighbors_for_articles_returns_enriched_neighbor_artifacts() -> None:
    session = _NeighborSession({1: [{'article_id': 2, 'similarity': 0.91, 'source': 'elmundo', 'title': 'Vecino', 'url': 'https://example.com/2', 'published_at': '2026-03-17T00:00:00+00:00', 'published_date': '2026-03-17', 'display_date': '2026-03-17', 'section': 'politica', 'summary_snippet': 'resumen vecino'}]})
    payload = load_neighbors_for_articles(session, article_ids=[1], limit=3)
    assert payload[1][0].article_id == 2
    assert payload[1][0].similarity == pytest.approx(0.91)


def test_load_explorer_points_page_joins_semantic_analysis_when_filters_need_it() -> None:
    session = _ExplorerSession()
    load_explorer_points_page(session, filters=ExplorerFilters(cluster_id=2, outlier_only=True))
    joined_sql = '\n'.join(session.sql)
    assert 'LEFT JOIN semantic_point_analysis spa' in joined_sql
    assert 'spa.cluster_id = :cluster_id' in joined_sql
    assert 'spa.is_outlier = :outlier_only' in joined_sql


def test_load_explorer_article_detail_formats_published_at_as_text_sql() -> None:
    session = _ExplorerSession()
    load_explorer_article_detail(session, article_id=1, projection_set='pca_2d_latest')
    sql = next(sql for sql in session.sql if 'FROM articles a' in sql)
    assert 'to_char(a.published_at AT TIME ZONE' in sql or 'CAST(a.published_at AS TEXT)' in sql


def test_resolve_semantic_window_supports_days_back_and_explicit_dates() -> None:
    assert resolve_semantic_window(days_back=3, today=date(2026, 3, 18)) == SemanticWindow(
        date_from='2026-03-16',
        date_to='2026-03-18',
    )
    assert resolve_semantic_window(date_from='2026-03-01', date_to='2026-03-05') == SemanticWindow(
        date_from='2026-03-01',
        date_to='2026-03-05',
    )


def test_resolve_semantic_window_rejects_invalid_combinations() -> None:
    with pytest.raises(ValueError, match='cannot be combined'):
        resolve_semantic_window(days_back=2, date_from='2026-03-01')
    with pytest.raises(ValueError, match='cannot be after'):
        resolve_semantic_window(date_from='2026-03-05', date_to='2026-03-01')


def test_select_embedding_candidates_applies_window_filters() -> None:
    row = _Row(id=1)
    session = _SelectSession([row], existing_by_article_id={})

    candidates = select_embedding_candidates(
        session,
        limit=10,
        max_chars=500,
        window=SemanticWindow(date_from='2026-03-10', date_to='2026-03-12'),
    )

    assert [candidate.article.article_id for candidate in candidates] == [1]
    assert any('window_date_from' in params for params in session.last_query.params_seen)
    assert any('window_date_to' in params for params in session.last_query.params_seen)


def test_load_projected_points_applies_window_filters_to_sql() -> None:
    session = _ExplorerSession()

    load_projected_points(
        session,
        projection_set='pca_3d_latest',
        window=SemanticWindow(date_from='2026-03-10', date_to='2026-03-12'),
    )

    sql = next(sql for sql in session.sql if 'FROM article_projections p' in sql and 'LIMIT :limit' not in sql)
    assert 'date(a.published_at) >= date(:window_date_from)' in sql
    assert 'date(a.published_at) <= date(:window_date_to)' in sql
    params = next(params for params in session.params if params.get('projection_set') == 'pca_3d_latest')
    assert params['window_date_from'] == '2026-03-10'
    assert params['window_date_to'] == '2026-03-12'


def test_projection_kind_for_set_distinguishes_2d_and_3d_sets() -> None:
    assert projection_kind_for_set('pca_2d_latest') == 'pca_2d'
    assert projection_kind_for_set('pca_3d_latest') == 'pca_3d'
