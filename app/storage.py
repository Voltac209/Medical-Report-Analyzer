from pathlib import Path
import re
from uuid import uuid4

from app.config import get_upload_dir


MAX_UPLOAD_BYTES = 15 * 1024 * 1024


class UploadValidationError(Exception):
    """Raised when an uploaded file is not acceptable for the PoC parser."""


def validate_pdf_upload(filename: str, content: bytes) -> None:
    if not filename.lower().endswith(".pdf"):
        raise UploadValidationError("Only PDF files are supported.")
    if not content:
        raise UploadValidationError("The uploaded PDF is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadValidationError("PDF files must be 15 MB or smaller for this PoC.")


def sanitize_filename(filename: str) -> str:
    filename = filename.replace("/", "_").replace("\\", "_")
    safe_name = Path(filename).name.strip().replace(" ", "_")
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)
    return safe_name or "report.pdf"


def save_uploaded_pdf(filename: str, content: bytes) -> Path:
    validate_pdf_upload(filename, content)

    upload_dir = get_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(filename)
    stored_path = upload_dir / f"{uuid4().hex}_{safe_name}"
    stored_path.write_bytes(content)
    return stored_path
