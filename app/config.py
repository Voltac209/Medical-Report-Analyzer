from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()


@lru_cache
def get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/medical_report_analyzer",
    )


@lru_cache
def get_upload_dir() -> Path:
    return Path(os.getenv("UPLOAD_DIR", "uploads"))


@lru_cache
def get_openai_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "")


@lru_cache
def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5.6")
