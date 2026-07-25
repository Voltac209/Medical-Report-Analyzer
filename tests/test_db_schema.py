import unittest

from app.db import SCHEMA_SQL


class DatabaseSchemaTests(unittest.TestCase):
    def test_schema_includes_lab_explanations(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS lab_explanations", SCHEMA_SQL)
        self.assertIn("plain_language_name TEXT NOT NULL", SCHEMA_SQL)
        self.assertIn("result_context TEXT NOT NULL", SCHEMA_SQL)
        self.assertIn("caution TEXT NOT NULL", SCHEMA_SQL)
        self.assertIn("source_page INTEGER", SCHEMA_SQL)


if __name__ == "__main__":
    unittest.main()
