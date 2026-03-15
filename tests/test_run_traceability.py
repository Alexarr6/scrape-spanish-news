import json
import unittest
from pathlib import Path

from tests.fixture_paths import EVIDENCE_ROOT


class RunTraceabilityTests(unittest.TestCase):
    def test_manifest_points_to_canonical_fixture_bundle(self):
        repo_root = Path(__file__).resolve().parents[1]
        fixture_root = EVIDENCE_ROOT
        manifest_path = fixture_root / "run_manifest.json"
        self.assertTrue(manifest_path.exists(), "fixture run_manifest.json is required")

        data = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(data["canonical_run_id"], "20260314-1212-8ff9")

        canonical_fixture_root = Path(data["canonical_fixture_root"])
        self.assertEqual(canonical_fixture_root.name, fixture_root.name)
        self.assertEqual(canonical_fixture_root.parent.name, fixture_root.parent.name)
        self.assertEqual(canonical_fixture_root.parts[-1], fixture_root.parts[-1])

        repository_root = Path(data["repository_root"])
        self.assertEqual(repository_root.name, repo_root.name)
        self.assertEqual(repository_root.parts[-1], repo_root.parts[-1])

        companion_fixture_root = Path(data["companion_docs_review"]["fixture_root"])
        self.assertEqual(data["companion_docs_review"]["run_id"], "20260314-1250-edr1")
        self.assertEqual(companion_fixture_root.name, fixture_root.name)
        self.assertEqual(companion_fixture_root.parent.name, fixture_root.parent.name)
        self.assertEqual(data["companion_docs_review"]["policy"], "docs-review-only")

        for cmd in data["verify_commands"]:
            self.assertIsInstance(cmd, str)
            self.assertTrue(cmd.strip())


if __name__ == "__main__":
    unittest.main()
