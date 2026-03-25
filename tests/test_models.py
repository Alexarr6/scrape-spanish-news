import unittest

from src.core.models import iso_to_local_date, parse_any_date_to_utc_iso


class ModelTests(unittest.TestCase):
    def test_parse_rfc822_date(self):
        out = parse_any_date_to_utc_iso("Sat, 14 Mar 2026 10:00:00 +0100")
        self.assertTrue(out.startswith("2026-03-14T09:00:00+00:00"))

    def test_iso_to_local_date_maps_utc_midnight_edges_to_madrid_day(self):
        out = iso_to_local_date("2026-03-22T23:03:33+00:00", "Europe/Madrid")
        self.assertEqual(out, "2026-03-23")


if __name__ == "__main__":
    unittest.main()
