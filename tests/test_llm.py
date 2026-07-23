import unittest

from app.llm import (
    LAB_OBSERVATION_SCHEMA,
    SIMPLIFICATION_SCHEMA,
    build_observation_context,
    build_report_text,
)


class LabExtractionTests(unittest.TestCase):
    def test_build_report_text_keeps_page_numbers(self):
        pages = [
            {"page_number": 1, "text_content": "Hemoglobin 13.5 g/dL"},
            {"page_number": 2, "text_content": ""},
            {"page_number": 3, "text_content": "HbA1c 5.8 %"},
        ]

        report_text = build_report_text(pages)

        self.assertIn("Page 1:", report_text)
        self.assertIn("Hemoglobin 13.5 g/dL", report_text)
        self.assertIn("Page 3:", report_text)
        self.assertNotIn("Page 2:", report_text)

    def test_schema_requires_source_references(self):
        observation_schema = LAB_OBSERVATION_SCHEMA["properties"]["observations"]["items"]

        self.assertIn("page_number", observation_schema["required"])
        self.assertIn("source_snippet", observation_schema["required"])
        self.assertFalse(observation_schema["additionalProperties"])

    def test_build_observation_context_includes_source_detail(self):
        observations = [
            {
                "test_name": "HbA1c",
                "value": 5.8,
                "unit": "%",
                "reference_range": "4.0-5.6",
                "abnormal_flag": "High",
                "page_number": 2,
                "source_snippet": "HbA1c 5.8 % High",
            }
        ]

        context = build_observation_context(observations)

        self.assertIn("Test: HbA1c", context)
        self.assertIn("Reference range: 4.0-5.6", context)
        self.assertIn("Source page: 2", context)
        self.assertIn("Source snippet: HbA1c 5.8 % High", context)

    def test_simplification_schema_requires_caution(self):
        explanation_schema = SIMPLIFICATION_SCHEMA["properties"]["explanations"]["items"]

        self.assertIn("caution", explanation_schema["required"])
        self.assertIn("source_page", explanation_schema["required"])
        self.assertFalse(explanation_schema["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
