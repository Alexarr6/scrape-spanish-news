import unittest

from src.adapters.registry import ADAPTERS


class RegistryTests(unittest.TestCase):
    def test_known_sources_present(self):
        self.assertIn("elpais", ADAPTERS)
        self.assertIn("elmundo", ADAPTERS)
        self.assertIn("abc", ADAPTERS)
        self.assertIn("lavanguardia", ADAPTERS)


if __name__ == "__main__":
    unittest.main()
