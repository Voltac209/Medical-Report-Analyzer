import pandas as pd
import streamlit as st

from app.db import (
    create_report,
    format_uploaded_at,
    get_report_pages,
    init_db,
    list_reports,
    replace_report_pages,
)
from app.pdf_parser import PdfParsingError, combined_preview, extract_pages, page_text_stats
from app.storage import UploadValidationError, save_uploaded_pdf


DISCLAIMER = """
This proof of concept is for educational use only. It is not medical advice, does
not diagnose conditions, may extract or simplify information incorrectly, and must
be reviewed with a licensed clinician before any health decision.
"""


def show_disclaimer() -> None:
    st.warning(DISCLAIMER)
    st.caption(
        "Privacy note: uploaded PDFs are stored locally for this demo, and metadata "
        "is stored in PostgreSQL. Do not upload sensitive real patient data."
    )


def initialize_database() -> bool:
    try:
        init_db()
        return True
    except Exception as exc:
        st.error("PostgreSQL is not reachable or is not configured correctly.")
        st.code(str(exc))
        st.info("Create the database, copy `.env.example` to `.env`, then restart Streamlit.")
        return False


def upload_report() -> None:
    st.subheader("Upload medical PDF")
    uploaded_file = st.file_uploader("Choose a PDF report", type=["pdf"])

    if uploaded_file is None:
        return

    if st.button("Parse and save report", type="primary"):
        try:
            content = uploaded_file.getvalue()
            stored_path = save_uploaded_pdf(uploaded_file.name, content)
            pages = extract_pages(stored_path)
            stats = page_text_stats(pages)
            status = "parsed" if stats["text_char_count"] else "needs_ocr"
            report_id = create_report(
                uploaded_file.name,
                stored_path,
                stats["page_count"],
                stats["text_page_count"],
                stats["text_char_count"],
                status,
            )
            replace_report_pages(report_id, pages)
        except UploadValidationError as exc:
            st.error(str(exc))
            return
        except PdfParsingError as exc:
            st.error(str(exc))
            st.info("Try a text-based lab report PDF. OCR for scanned reports is planned later.")
            return
        except Exception as exc:
            st.error("Could not parse and save this report.")
            st.code(str(exc))
            return

        st.success(f"Saved report #{report_id} with {stats['page_count']} pages.")
        st.caption(
            f"Selectable text found on {stats['text_page_count']} page(s), "
            f"{stats['text_char_count']} characters total."
        )
        preview = combined_preview(pages)
        if preview:
            st.text_area("Extracted text preview", preview, height=320)
        else:
            st.warning(
                "No selectable text was found. This is likely a scanned PDF; OCR support is a future enhancement."
            )


def report_history() -> None:
    st.subheader("Recent uploads")
    try:
        reports = list_reports()
    except Exception as exc:
        st.error("Could not load reports from PostgreSQL.")
        st.code(str(exc))
        return

    if not reports:
        st.info("No reports uploaded yet.")
        return

    frame = pd.DataFrame(
        [
            {
                "ID": report["id"],
                "Filename": report["original_filename"],
                "Pages": report["page_count"],
                "Text pages": report["text_page_count"],
                "Text chars": report["text_char_count"],
                "Status": report["status"],
                "Uploaded": format_uploaded_at(report["uploaded_at"]),
            }
            for report in reports
        ]
    )
    st.dataframe(frame, hide_index=True, use_container_width=True)

    selected_id = st.selectbox(
        "Preview stored page text",
        options=[report["id"] for report in reports],
        format_func=lambda report_id: next(
            report["original_filename"] for report in reports if report["id"] == report_id
        ),
    )
    pages = get_report_pages(selected_id)
    if pages:
        preview_pages = [
            {"page_number": page["page_number"], "text": page["text_content"]}
            for page in pages
        ]
        st.text_area("Stored source text", combined_preview(preview_pages), height=260)
    else:
        st.info("This report has no stored selectable text yet.")


def main() -> None:
    st.set_page_config(page_title="Medical Report Simplifier", layout="wide")
    st.title("Medical Report Simplifier")
    show_disclaimer()

    db_ready = initialize_database()
    if not db_ready:
        return

    left, right = st.columns([1, 1])
    with left:
        upload_report()
    with right:
        report_history()


if __name__ == "__main__":
    main()
