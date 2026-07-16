import pandas as pd
import streamlit as st

from app.db import create_report, format_uploaded_at, init_db, list_reports, replace_report_pages
from app.pdf_parser import combined_preview, extract_pages
from app.storage import save_uploaded_pdf


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
            stored_path = save_uploaded_pdf(uploaded_file.name, uploaded_file.getvalue())
            pages = extract_pages(stored_path)
            report_id = create_report(uploaded_file.name, stored_path, len(pages))
            replace_report_pages(report_id, pages)
        except Exception as exc:
            st.error("Could not parse and save this report.")
            st.code(str(exc))
            return

        st.success(f"Saved report #{report_id} with {len(pages)} pages.")
        preview = combined_preview(pages)
        if preview:
            st.text_area("Extracted text preview", preview, height=320)
        else:
            st.warning("No selectable text was found. OCR support is a future enhancement.")


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
                "Status": report["status"],
                "Uploaded": format_uploaded_at(report["uploaded_at"]),
            }
            for report in reports
        ]
    )
    st.dataframe(frame, hide_index=True, use_container_width=True)


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
