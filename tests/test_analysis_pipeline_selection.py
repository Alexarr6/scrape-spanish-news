from datetime import datetime, timezone

from src.analysis.pipeline import AnalysisPipeline


class _Row:
    def __init__(self, article_id: int, source: str) -> None:
        self.id = article_id
        self.source = source
        self.published_at = datetime(2026, 3, 24, tzinfo=timezone.utc)


def test_select_source_balanced_enrichment_rows_round_robins_sources() -> None:
    pipeline = AnalysisPipeline.__new__(AnalysisPipeline)
    rows = [
        _Row(1, "elpais"),
        _Row(2, "elpais"),
        _Row(3, "elpais"),
        _Row(4, "elmundo"),
        _Row(5, "eldiario"),
    ]

    selected = pipeline._select_source_balanced_enrichment_rows(rows, limit=4)

    assert [row.id for row in selected] == [1, 4, 5, 2]
