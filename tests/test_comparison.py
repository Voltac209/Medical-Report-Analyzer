import unittest
from decimal import Decimal

from app.comparison import build_trend_points, normalize_lab_name, repeated_lab_names


class ComparisonTests(unittest.TestCase):
    def test_normalize_lab_name_handles_common_aliases(self):
        self.assertEqual(normalize_lab_name("Hemoglobin A1c"), "hba1c")
        self.assertEqual(normalize_lab_name("Hb A1C"), "hba1c")
        self.assertEqual(normalize_lab_name("Total Cholesterol"), "cholesterol total")

    def test_build_trend_points_keeps_numeric_observations(self):
        observations = [
            {
                "report_id": 1,
                "original_filename": "jan.pdf",
                "test_name": "HbA1c",
                "normalized_name": None,
                "value": Decimal("5.8"),
                "unit": "%",
                "reference_range": "4.0-5.6",
                "abnormal_flag": "High",
                "report_date": "2026-01-01",
                "page_number": 1,
                "source_snippet": "HbA1c 5.8 % High",
            },
            {
                "report_id": 2,
                "original_filename": "feb.pdf",
                "test_name": "Comment",
                "normalized_name": None,
                "value": None,
            },
        ]

        trend_points = build_trend_points(observations)

        self.assertEqual(len(trend_points), 1)
        self.assertEqual(trend_points[0]["Normalized test"], "hba1c")
        self.assertEqual(trend_points[0]["Value"], 5.8)

    def test_repeated_lab_names_require_multiple_reports(self):
        trend_points = [
            {"Report ID": 1, "Normalized test": "hba1c"},
            {"Report ID": 1, "Normalized test": "hba1c"},
            {"Report ID": 2, "Normalized test": "hba1c"},
            {"Report ID": 1, "Normalized test": "hemoglobin"},
        ]

        self.assertEqual(repeated_lab_names(trend_points), ["hba1c"])


if __name__ == "__main__":
    unittest.main()
