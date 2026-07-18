import unittest

from app.storage import UploadValidationError, sanitize_filename, validate_pdf_upload


class StorageTests(unittest.TestCase):
    def test_sanitize_filename_removes_path_and_unsafe_characters(self):
        self.assertEqual(
            sanitize_filename("Lab Report 7/18 (Final).pdf"),
            "Lab_Report_7_18__Final_.pdf",
        )

    def test_validate_pdf_upload_rejects_non_pdf(self):
        with self.assertRaises(UploadValidationError):
            validate_pdf_upload("report.txt", b"content")

    def test_validate_pdf_upload_rejects_empty_file(self):
        with self.assertRaises(UploadValidationError):
            validate_pdf_upload("report.pdf", b"")


if __name__ == "__main__":
    unittest.main()
