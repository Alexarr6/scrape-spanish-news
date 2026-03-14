# RUN_MANIFEST.md

Canonical implementation run for Phase-1 quick wins.

- canonical_run_id: `20260314-1212-8ff9`
- canonical_run_root: `/home/node/.openclaw/workspace/repos/spain-news-bias-scraper/runs/20260314-1212-8ff9`
- repository_root: `/home/node/.openclaw/workspace/repos/spain-news-bias-scraper`
- companion_docs_review_run_id: `20260314-1250-edr1`
- companion_docs_review_run_root: `/home/node/.openclaw/workspace/repos/spain-news-bias-scraper/runs/20260314-1250-edr1`
- companion_run_policy: `docs/review only; do not execute implementation commands from companion run`

## Reproducible verification commands (run from canonical_run_root)

```bash
pwd
python3 -m src.main --help
python3 -m unittest discover -s tests -v
python3 scripts/generate_comparison_summary.py --date 2026-03-13 --out logs/comparison_summary.json
```

## Machine-readable pointer

See `run_manifest.json` in this same run root.
