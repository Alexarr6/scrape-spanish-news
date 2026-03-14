import unittest

from src.adapters.abc import ABCAdapter


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


if __name__ == "__main__":
    unittest.main()
