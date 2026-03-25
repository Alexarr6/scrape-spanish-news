from __future__ import annotations

import unittest

from src.adapters.minutos20 import Minutos20Adapter
from src.core.adapter import RunConfig


class _FakeHttp:
    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping

    def get_text(self, url: str) -> str:
        if url not in self.mapping:
            raise RuntimeError(f"missing fixture for {url}")
        return self.mapping[url]


class Minutos20Tests(unittest.TestCase):
    def test_discovery_layers_rss_sitemap_html(self):
        feed = """
            <rss><channel>
              <item><link>https://www.20minutos.es/nacional/2026/03/13/uno_111_0.html</link></item>
              <item><link>https://www.20minutos.es/deportes/2026/03/13/nope_222_0.html</link></item>
            </channel></rss>
        """
        sitemap = """
            <urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
              <url><loc>https://www.20minutos.es/politica/2026/03/13/dos_333_0.html</loc></url>
            </urlset>
        """
        html = '<a href="https://www.20minutos.es/espana/2026/03/13/tres_444_0.html">ok</a>'

        adapter = Minutos20Adapter(
            http_client=_FakeHttp(
                {
                    "https://www.20minutos.es/rss/": feed,
                    "https://www.20minutos.es/rss/nacional/": "<rss><channel></channel></rss>",
                    "https://www.20minutos.es/rss/actualidad/": "<rss><channel></channel></rss>",
                    "https://www.20minutos.es/sitemap-noticias.xml": sitemap,
                    "https://www.20minutos.es/sitemap-news.xml": "<urlset></urlset>",
                    "https://www.20minutos.es/sitemap.xml": "<urlset></urlset>",
                    "https://www.20minutos.es/nacional/": html,
                    "https://www.20minutos.es/minuteca/politica/": "",
                    "https://www.20minutos.es/minuteca/espana/": "",
                }
            )
        )

        urls = adapter.discover("2026-03-13", RunConfig(max_discovery_urls=50))
        self.assertIn("https://www.20minutos.es/nacional/2026/03/13/uno_111_0.html", urls)
        self.assertIn("https://www.20minutos.es/politica/2026/03/13/dos_333_0.html", urls)
        self.assertIn("https://www.20minutos.es/espana/2026/03/13/tres_444_0.html", urls)
        self.assertNotIn("https://www.20minutos.es/deportes/2026/03/13/nope_222_0.html", urls)

    def test_run_emits_strategy_metrics_envelope(self):
        adapter = Minutos20Adapter(http_client=_FakeHttp({}))

        def _fake_discover(*, target_date, cfg):
            adapter._strategy_metrics = [
                {
                    "strategy_name": "rss_discovery",
                    "attempted": 3,
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
        self.assertEqual(
            metrics["strategy_metrics"]["schema_version"],
            "discovery_strategy_metrics.v1",
        )
        self.assertIsInstance(metrics["strategy_metrics"]["strategies"], list)


if __name__ == "__main__":
    unittest.main()
