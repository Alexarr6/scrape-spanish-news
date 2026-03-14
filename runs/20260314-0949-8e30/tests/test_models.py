import unittest

from src.core.models import parse_any_date_to_utc_iso


class ModelTests(unittest.TestCase):
    def test_parse_rfc822_date(self):
        out = parse_any_date_to_utc_iso("Sat, 14 Mar 2026 10:00:00 +0100")
        self.assertTrue(out.startswith("2026-03-14T09:00:00+00:00"))


if __name__ == "__main__":
    unittest.main()
