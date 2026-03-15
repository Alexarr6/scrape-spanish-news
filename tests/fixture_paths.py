from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
EVIDENCE_ROOT = TESTS_ROOT / "fixtures" / "evidence" / "20260314-1212-8ff9"


def pick_existing(root: Path, candidates: list[str]) -> Path:
    for rel in candidates:
        path = root / rel
        if path.exists():
            return path
    raise AssertionError(f"missing all candidates: {candidates}")
