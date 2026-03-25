from __future__ import annotations

import unittest

from src.adapters.eldiario import ElDiarioAdapter
from src.adapters.layered_discovery import DiscoveryLayer, run_layered_discovery
from src.core.adapter import RunConfig


class _FakeHttp:
    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping

    def get_text(self, url: str) -> str:
        if url not in self.mapping:
            raise RuntimeError(f"missing fixture for {url}")
        return self.mapping[url]


class ElDiarioTests(unittest.TestCase):
    def test_discovery_layers_rss_robots_sitemap_html(self):
        feed = """
            <rss><channel>
              <item><link>https://www.eldiario.es/politica/2026/03/13/uno.html</link></item>
              <item><link>https://www.eldiario.es/deportes/2026/03/13/nope.html</link></item>
            </channel></rss>
        """
        robots = """
            User-agent: *
            Sitemap: https://www.eldiario.es/sitemap_index_25b87.xml
        """
        sitemap = """
            <urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
              <url><loc>https://www.eldiario.es/sociedad/2026/03/13/dos.html</loc></url>
            </urlset>
        """
        html = '<a href="https://www.eldiario.es/nacional/2026/03/13/tres.html">ok</a>'

        adapter = ElDiarioAdapter(
            http_client=_FakeHttp(
                {
                    "https://www.eldiario.es/rss/": feed,
                    "https://www.eldiario.es/rss/politica/": "<rss><channel></channel></rss>",
                    "https://www.eldiario.es/rss/sociedad/": "<rss><channel></channel></rss>",
                    "https://www.eldiario.es/robots.txt": robots,
                    "https://www.eldiario.es/sitemap_index.xml": "<sitemapindex></sitemapindex>",
                    "https://www.eldiario.es/sitemap_google_news.xml": "<urlset></urlset>",
                    "https://www.eldiario.es/sitemap.xml": "<urlset></urlset>",
                    "https://www.eldiario.es/sitemap_index_25b87.xml": sitemap,
                    "https://www.eldiario.es/politica/": html,
                    "https://www.eldiario.es/sociedad/": "",
                    "https://www.eldiario.es/": "",
                }
            )
        )

        urls = adapter.discover("2026-03-13", RunConfig(max_discovery_urls=50))
        self.assertIn("https://www.eldiario.es/politica/2026/03/13/uno.html", urls)
        self.assertIn("https://www.eldiario.es/sociedad/2026/03/13/dos.html", urls)
        self.assertIn("https://www.eldiario.es/nacional/2026/03/13/tres.html", urls)
        self.assertNotIn("https://www.eldiario.es/deportes/2026/03/13/nope.html", urls)

    def test_run_emits_strategy_metrics_envelope(self):
        adapter = ElDiarioAdapter(http_client=_FakeHttp({}))

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

    def test_usable_candidate_thresholds_do_not_skip_on_raw_stale_volume(self):
        adapter = ElDiarioAdapter(http_client=_FakeHttp({}))
        stale_urls = [
            f"https://www.eldiario.es/politica/2026/03/10/stale-{idx}.html" for idx in range(12)
        ]
        fresh_html = ["https://www.eldiario.es/nacional/2026/03/13/fresh.html"]

        urls, metrics = run_layered_discovery(
            cfg=RunConfig(max_discovery_urls=50),
            accept=adapter._accept,
            reject_noise=adapter._reject_noise,
            layers=[
                DiscoveryLayer(
                    strategy_name="rss_discovery",
                    load_candidates=lambda: (stale_urls, 0),
                ),
                DiscoveryLayer(
                    strategy_name="html_fallback_discovery",
                    load_candidates=lambda: (fresh_html, 0),
                    should_skip=lambda urls: adapter._has_enough_usable_candidates(
                        urls, target_date="2026-03-13", minimum=10
                    ),
                ),
            ],
        )

        self.assertIn(fresh_html[0], urls)
        html_metrics = next(item for item in metrics if item["strategy_name"] == "html_fallback_discovery")
        self.assertEqual(html_metrics["accepted"], 1)


if __name__ == "__main__":
    unittest.main()
