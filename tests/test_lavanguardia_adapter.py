from __future__ import annotations

import unittest

from src.adapters.lavanguardia import LaVanguardiaAdapter
from src.adapters.url_filters import is_probable_noise_url
from src.core.adapter import RunConfig


class _FakeHttp:
    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping

    def get_text(self, url: str) -> str:
        if url not in self.mapping:
            raise RuntimeError(f"missing fixture for {url}")
        return self.mapping[url]


class LaVanguardiaTests(unittest.TestCase):
    def test_whitelist_and_discovery_layers(self):
        feed = """
            <rss><channel>
              <item><link>https://www.lavanguardia.com/politica/2026/03/13/foo.html</link></item>
              <item><link>https://www.lavanguardia.com/cultura/2026/03/13/nope.html</link></item>
            </channel></rss>
        """
        sitemap = """
            <urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
              <url><loc>https://www.lavanguardia.com/espana/2026/03/13/bar.html</loc></url>
            </urlset>
        """
        html = '<a href="https://www.lavanguardia.com/nacional/2026/03/13/baz.html">ok</a>'

        adapter = LaVanguardiaAdapter(
            http_client=_FakeHttp(
                {
                    "https://www.lavanguardia.com/rss/home.xml": feed,
                    (
                        "https://www.lavanguardia.com/rss/politica.xml"
                    ): "<rss><channel></channel></rss>",
                    (
                        "https://www.lavanguardia.com/rss/nacional.xml"
                    ): "<rss><channel></channel></rss>",
                    "https://www.lavanguardia.com/sitemap.xml": sitemap,
                    "https://www.lavanguardia.com/sitemap-noticias.xml": "<urlset></urlset>",
                    "https://www.lavanguardia.com/politica": html,
                    "https://www.lavanguardia.com/politica/nacional": "",
                    "https://www.lavanguardia.com/vida": "",
                    "https://www.lavanguardia.com/vida/espana": "",
                    "https://www.lavanguardia.com/nacional": "",
                }
            )
        )

        urls = adapter.discover("2026-03-13", RunConfig(max_discovery_urls=50))
        self.assertIn("https://www.lavanguardia.com/politica/2026/03/13/foo.html", urls)
        self.assertIn("https://www.lavanguardia.com/espana/2026/03/13/bar.html", urls)
        self.assertIn("https://www.lavanguardia.com/nacional/2026/03/13/baz.html", urls)
        self.assertNotIn("https://www.lavanguardia.com/cultura/2026/03/13/nope.html", urls)

    def test_rejects_static_asset_noise_url(self):
        self.assertTrue(
            is_probable_noise_url(
                "https://www.lavanguardia.com/media/2026/03/23/portada-politica.webp"
            )
        )

    def test_discover_prioritizes_same_day_urls_over_stale_urls(self):
        adapter = LaVanguardiaAdapter(http_client=_FakeHttp({}))
        adapter._discover_links_from_feeds = lambda feeds: (
            [
                "https://www.lavanguardia.com/politica/2025/12/01/very-old.html",
                "https://www.lavanguardia.com/politica/2026/03/23/fresh.html",
                "https://www.lavanguardia.com/politica/2026/03/22/nearby.html",
            ],
            0,
        )
        adapter._discover_links_from_sitemaps = lambda sitemaps: ([], 0)
        adapter._discover_links_from_html_pages = lambda pages: ([], 0)

        urls = adapter.discover("2026-03-23", RunConfig(max_discovery_urls=10))

        self.assertEqual(
            urls,
            [
                "https://www.lavanguardia.com/politica/2026/03/23/fresh.html",
                "https://www.lavanguardia.com/politica/2026/03/22/nearby.html",
                "https://www.lavanguardia.com/politica/2025/12/01/very-old.html",
            ],
        )

    def test_run_emits_strategy_metrics_envelope(self):
        adapter = LaVanguardiaAdapter(http_client=_FakeHttp({}))

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
