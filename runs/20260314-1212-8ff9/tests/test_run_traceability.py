import json
import unittest
from pathlib import Path


class RunTraceabilityTests(unittest.TestCase):
    def test_manifest_points_to_canonical_run(self):
        run_root = Path(__file__).resolve().parents[1]
        manifest_path = run_root / "run_manifest.json"
        self.assertTrue(manifest_path.exists(), "run_manifest.json is required")

        data = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(data["canonical_run_id"], "20260314-1212-8ff9")
        self.assertEqual(Path(data["canonical_run_root"]), run_root)
        self.assertEqual(data["companion_docs_review"]["run_id"], "20260314-1250-edr1")
        self.assertEqual(data["companion_docs_review"]["policy"], "docs-review-only")

        for cmd in data["verify_commands"]:
            self.assertIsInstance(cmd, str)
            self.assertTrue(cmd.strip())


if __name__ == "__main__":
    unittest.main()
