from src.analysis.pipeline import ClusterPipeline
from src.analysis.story_eval import evaluate_fixture, load_fixture_dataset


FIXTURE_PATH = "tests/fixtures/story_matching_eval_fixture.json"


def test_story_matching_eval_baseline_exposes_followup_recall_gap() -> None:
    dataset = load_fixture_dataset(FIXTURE_PATH)
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]

    result = evaluate_fixture(pipeline, dataset)

    assert result.pair_summary is not None
    assert result.cluster_summary is not None
    assert result.pair_summary.true_positive_count == 1
    assert result.pair_summary.false_negative_count == 2
    assert result.pair_summary.false_positive_count == 0
    assert result.pair_summary.precision == 1.0
    assert result.pair_summary.recall == 0.3333
    assert result.cluster_summary.recall == 0.3333
    assert result.predicted_components == [[1, 2], [3], [4], [5], [6]]
