import unittest

from app.pdf_parser import page_text_stats


class PageTextStatsTests(unittest.TestCase):
    def test_counts_pages_with_selectable_text(self):
        pages = [
            {"page_number": 1, "text": "Hemoglobin 13.2 g/dL"},
            {"page_number": 2, "text": "   "},
            {"page_number": 3, "text": "HbA1c 5.6 %"},
        ]

        stats = page_text_stats(pages)

        self.assertEqual(stats["page_count"], 3)
        self.assertEqual(stats["text_page_count"], 2)
        self.assertEqual(stats["text_char_count"], 31)


if __name__ == "__main__":
    unittest.main()
