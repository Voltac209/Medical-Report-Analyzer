from pathlib import Path

import pdfplumber


def extract_pages(pdf_path: Path) -> list[dict]:
    pages: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(
                {
                    "page_number": index,
                    "text": text.strip(),
                }
            )
    return pages


def combined_preview(pages: list[dict], max_chars: int = 5000) -> str:
    chunks = []
    for page in pages:
        if not page["text"]:
            continue
        chunks.append(f"--- Page {page['page_number']} ---\n{page['text']}")
    return "\n\n".join(chunks)[:max_chars]
