import unittest

from src.adapters.abc import ABCAdapter
from src.core.adapter import RunConfig


class ABCTests(unittest.TestCase):
    def test_parse_sitemap(self):
        adapter = ABCAdapter()
        xml = """<urlset><url><loc>https://www.abc.es/espana/test.html</loc></url></urlset>"""
        links = adapter._parse_sitemap(xml)
        self.assertEqual(links, ["https://www.abc.es/espana/test.html"])

    def test_accept_filters_non_spain_urls(self):
        adapter = ABCAdapter()
        seen = set()
        self.assertTrue(adapter._accept("https://www.abc.es/espana/x.html", seen))
        self.assertFalse(adapter._accept("https://www.abc.es/cultura/x.html", seen))

    def test_run_emits_strategy_metrics_envelope(self):
        adapter = ABCAdapter()

        def _fake_discover(*, target_date, cfg):
            adapter._strategy_metrics = [
                {
                    "strategy_name": "rss_discovery",
                    "attempted": 2,
                    "accepted": 1,
                    "errors": 0,
                    "stop_reason": "completed",
                    "elapsed_ms": 0,
                }
            ]
            return []

        adapter.discover = _fake_discover
        _, metrics = adapter.run("2026-03-13", RunConfig())
        self.assertIn("strategy_metrics", metrics)
        self.assertEqual(metrics["strategy_metrics"]["schema_version"], "discovery_strategy_metrics.v1")
        self.assertIsInstance(metrics["strategy_metrics"]["strategies"], list)


if __name__ == "__main__":
    unittest.main()
