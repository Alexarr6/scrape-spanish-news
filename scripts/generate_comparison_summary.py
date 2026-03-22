from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RUN_ROOT = Path(__file__).resolve().parents[1]
if str(RUN_ROOT) not in sys.path:
    sys.path.insert(0, str(RUN_ROOT))

DATE_DEFAULT = "2026-03-13"
SOURCES_DEFAULT = ["20minutos", "abc", "eldiario", "elmundo", "elpais", "lavanguardia"]


def _pick_existing(paths: list[Path]) -> Path:
    for p in paths:
        if p.exists():
            return p
    raise FileNotFoundError(f"no candidate exists: {', '.join(str(p) for p in paths)}")


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate normalized comparison_summary v1")
    p.add_argument("--date", default=DATE_DEFAULT)
    p.add_argument("--out", default="logs/comparison_summary.json")
    p.add_argument("--baseline-ref", default="canon2")
    p.add_argument("--current-ref", default="reg2")
    p.add_argument("--sources", nargs="*", default=SOURCES_DEFAULT)
    return p.parse_args()


def main() -> int:
    from src.core.comparison_summary import SourceSnapshot, build_comparison_summary

    args = _parse_args()
    snapshots: list[SourceSnapshot] = []

    for source in args.sources:
        baseline_path = _pick_existing(
            [
                Path(f"data/canon2_{source}_{args.date}.json"),
                Path(f"data/canon_{source}_{args.date}.json"),
                Path(f"data/news_{source}_{args.date}.json"),
            ]
        )
        current_path = _pick_existing(
            [
                Path(f"data/reg2_{source}_{args.date}.json"),
                Path(f"data/reg_{source}_{args.date}.json"),
                Path(f"data/news_{source}_{args.date}.json"),
            ]
        )
        metrics_path = _pick_existing(
            [
                Path(f"logs/reg2_{source}_metrics.json"),
                Path(f"logs/reg_{source}_metrics.json"),
                Path(f"logs/news_{source}_metrics.json"),
                Path(f"logs/canon2_{source}_metrics.json"),
                Path(f"logs/canon_{source}_metrics.json"),
            ]
        )

        baseline = _read_json(baseline_path)
        current = _read_json(current_path)
        metrics = _read_json(metrics_path)

        snapshots.append(
            SourceSnapshot(
                source=source,
                baseline_count=len(baseline),
                current_count=len(current),
                metrics=metrics,
            )
        )

    summary = build_comparison_summary(
        date=args.date,
        baseline_ref=args.baseline_ref,
        current_ref=args.current_ref,
        snapshots=snapshots,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"wrote {out} with {len(summary['sources'])} source rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
