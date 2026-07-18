from pathlib import Path

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError


class PdfParsingError(Exception):
    """Raised when a PDF cannot be opened or parsed as selectable text."""


def page_text_stats(pages: list[dict]) -> dict:
    text_pages = [page for page in pages if page["text"].strip()]
    return {
        "page_count": len(pages),
        "text_page_count": len(text_pages),
        "text_char_count": sum(len(page["text"]) for page in text_pages),
    }


def extract_pages(pdf_path: Path) -> list[dict]:
    pages: list[dict] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append(
                    {
                        "page_number": index,
                        "text": text.strip(),
                    }
                )
    except (PDFSyntaxError, ValueError, OSError) as exc:
        raise PdfParsingError("The uploaded file could not be read as a valid PDF.") from exc
    return pages


def combined_preview(pages: list[dict], max_chars: int = 5000) -> str:
    chunks = []
    for page in pages:
        if not page["text"]:
            continue
        chunks.append(f"--- Page {page['page_number']} ---\n{page['text']}")
    return "\n\n".join(chunks)[:max_chars]
