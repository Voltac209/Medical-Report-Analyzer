from pathlib import Path
from uuid import uuid4

from app.config import get_upload_dir


def save_uploaded_pdf(filename: str, content: bytes) -> Path:
    upload_dir = get_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename).name.replace(" ", "_")
    stored_path = upload_dir / f"{uuid4().hex}_{safe_name}"
    stored_path.write_bytes(content)
    return stored_path
