import unittest

from src.core.text_normalization import normalize_text


class TextNormalizationTests(unittest.TestCase):
    def test_repairs_common_mojibake_sequences(self):
        self.assertEqual(normalize_text("informaciÃ³n"), "información")
        self.assertEqual(normalize_text("JosÃ© MarÃ­a"), "José María")

    def test_removes_replacement_and_control_chars(self):
        self.assertEqual(normalize_text("Hola\u0007 mundo�"), "Hola mundo")

    def test_keeps_clean_text_stable(self):
        clean = "María Jesús Montero"
        self.assertEqual(normalize_text(clean), clean)


if __name__ == "__main__":
    unittest.main()
