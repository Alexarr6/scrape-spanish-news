from __future__ import annotations

import argparse
from pathlib import Path

from src.analysis.editorial_replay import evaluate_replay_corpus, render_replay_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Replay captured editorial-analysis fixtures through the "
            "local normalization pipeline."
        )
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=None,
        help="Override fixture directory (defaults to tests/fixtures/editorial_replay).",
    )
    args = parser.parse_args()

    results = evaluate_replay_corpus(args.fixtures_dir)
    print(render_replay_report(results))
    return 0 if all(result.status == "pass" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
