from src.analysis.clustering import ClusterPipeline
from src.analysis.ops.story_eval import build_pair_artifacts, load_fixture_dataset
from src.analysis.ops.story_review import (
    build_review_batch,
    build_threshold_sweep,
    summarize_review_labels,
    sweep_thresholds_against_review_labels,
)

FIXTURE_PATH = "tests/fixtures/story_matching_eval_fixture.json"


def test_threshold_sweep_shows_recall_tradeoff_on_fixture() -> None:
    dataset = load_fixture_dataset(FIXTURE_PATH)
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]

    rows = build_threshold_sweep(
        pipeline,
        dataset.articles,
        dataset.pair_labels,
        dataset.gold_clusters,
        thresholds=[0.68, 0.55],
    )

    assert [row.threshold for row in rows] == [0.68, 0.55]
    assert rows[0].pair_summary is not None
    assert rows[1].pair_summary is not None
    assert rows[0].cluster_summary is not None
    assert rows[1].cluster_summary is not None
    assert rows[1].accepted_pair_count >= rows[0].accepted_pair_count
    assert rows[1].pair_summary.recall >= rows[0].pair_summary.recall
    assert rows[1].cluster_summary.recall >= rows[0].cluster_summary.recall
    assert rows[1].predicted_cluster_count <= rows[0].predicted_cluster_count


def test_review_batch_is_small_and_auditable() -> None:
    dataset = load_fixture_dataset(FIXTURE_PATH)
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    artifacts, _, _ = build_pair_artifacts(pipeline, dataset.articles)

    rows = build_review_batch(artifacts, dataset.articles, score_threshold=0.68, batch_size=5)

    assert 1 <= len(rows) <= 5
    assert all(row.left["title"] for row in rows)
    assert all(row.right["summary"] for row in rows)
    assert any(row.bucket == "borderline" for row in rows)


def test_review_feedback_summary_and_threshold_sweep_ignore_uncertain() -> None:
    dataset = load_fixture_dataset(FIXTURE_PATH)
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    artifacts, _, _ = build_pair_artifacts(pipeline, dataset.articles)
    rows = build_review_batch(artifacts, dataset.articles, score_threshold=0.68, batch_size=5)

    assert len(rows) >= 3
    rows[0].label = "same_event"
    rows[1].label = "different_event"
    rows[2].label = "uncertain"

    summary = summarize_review_labels(rows)
    sweep = sweep_thresholds_against_review_labels(artifacts, rows, thresholds=[0.68, 0.55])

    assert summary["labeled_count"] == 3
    assert summary["decided_count"] == 2
    assert summary["uncertain_count"] == 1
    assert len(sweep) == 2
    assert all(item["pair_summary"] is not None for item in sweep)
