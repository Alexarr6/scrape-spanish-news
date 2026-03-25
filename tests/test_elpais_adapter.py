from __future__ import annotations

import unittest

from src.adapters.elpais import ElPaisAdapter
from src.core.adapter import RunConfig


class _FakeHttp:
    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping

    def get_text(self, url: str) -> str:
        if url not in self.mapping:
            raise RuntimeError(f"missing fixture for {url}")
        return self.mapping[url]


class ElPaisTests(unittest.TestCase):
    def test_discovery_prefers_hard_news_and_drops_opinion(self):
        feed = """
            <rss><channel>
              <item>
                <title>El Gobierno aprueba el decreto</title>
                <link>https://elpais.com/espana/2026-03-13/decreto.html</link>
                <pubDate>Fri, 13 Mar 2026 10:00:00 +0100</pubDate>
              </item>
              <item>
                <title>Columna personal</title>
                <link>https://elpais.com/opinion/2026-03-13/columna.html</link>
                <pubDate>Fri, 13 Mar 2026 09:00:00 +0100</pubDate>
              </item>
            </channel></rss>
        """
        adapter = ElPaisAdapter(
            http_client=_FakeHttp(
                {
                    "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada": feed,
                    (
                        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/espana/portada"
                    ): "<rss><channel></channel></rss>",
                    (
                        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada"
                    ): "<rss><channel></channel></rss>",
                    (
                        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada"
                    ): "<rss><channel></channel></rss>",
                    "https://elpais.com/sitemaps/news.xml": "<urlset></urlset>",
                    "https://elpais.com/sitemaps/sitemap.xml": "<urlset></urlset>",
                    "https://elpais.com/espana/": "",
                    "https://elpais.com/internacional/": "",
                    "https://elpais.com/economia/": "",
                }
            )
        )

        urls = adapter.discover("2026-03-13", RunConfig(max_discovery_urls=20))

        self.assertIn("https://elpais.com/espana/2026-03-13/decreto.html", urls)
        self.assertNotIn("https://elpais.com/opinion/2026-03-13/columna.html", urls)


if __name__ == "__main__":
    unittest.main()
