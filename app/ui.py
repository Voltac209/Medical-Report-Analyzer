import pandas as pd
import plotly.express as px
import streamlit as st

from app.comparison import build_trend_points, repeated_lab_names, summarize_trend
from app.db import (
    create_report,
    format_uploaded_at,
    get_lab_observations_for_reports,
    get_lab_explanations,
    get_lab_observations,
    get_report_pages,
    init_db,
    list_reports,
    replace_lab_explanations,
    replace_lab_observations,
    replace_report_pages,
)
from app.llm import (
    LabExtractionError,
    SimplificationError,
    extract_lab_observations,
    simplify_lab_observations,
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


def show_app_header() -> None:
    st.title("Medical Report Simplifier")
    st.caption("Upload reports, extract lab values, simplify results, and compare trends.")


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
    st.caption("Use text-based lab-report PDFs. Scanned PDFs need OCR, which is planned later.")
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


def run_full_analysis(report_id: int, pages: list[dict]) -> tuple[int, int]:
    extracted = extract_lab_observations(pages)
    replace_lab_observations(report_id, extracted)

    explanations = simplify_lab_observations(extracted)
    replace_lab_explanations(report_id, explanations)
    return len(extracted), len(explanations)


def observation_table(lab_observations: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Test": observation["test_name"],
                "Value": observation["value"],
                "Unit": observation["unit"],
                "Reference range": observation["reference_range"],
                "Flag": observation["abnormal_flag"],
                "Date": observation["report_date"],
                "Page": observation["page_number"],
                "Source": observation["source_snippet"],
            }
            for observation in lab_observations
        ]
    )


def reports_table(reports: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
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


def explanation_table(lab_explanations: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Test": explanation["test_name"],
                "Plain name": explanation["plain_language_name"],
                "Explanation": explanation["explanation"],
                "Result context": explanation["result_context"],
                "Caution": explanation["caution"],
                "Source page": explanation["source_page"],
            }
            for explanation in lab_explanations
        ]
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

    parsed_reports = [report for report in reports if report["status"] == "parsed"]
    no_text_reports = [report for report in reports if report["status"] == "needs_ocr"]

    metric_cols = st.columns(3)
    metric_cols[0].metric("Reports", len(reports))
    metric_cols[1].metric("Text-based", len(parsed_reports))
    metric_cols[2].metric("Need OCR", len(no_text_reports))

    st.dataframe(reports_table(reports), hide_index=True, use_container_width=True)

    selected_id = st.selectbox(
        "Select a report",
        options=[report["id"] for report in reports],
        format_func=lambda report_id: next(
            report["original_filename"] for report in reports if report["id"] == report_id
        ),
    )
    pages = get_report_pages(selected_id)
    lab_observations = get_lab_observations(selected_id)
    lab_explanations = get_lab_explanations(selected_id)
    has_source_text = bool(pages)

    st.caption(
        f"Stored analysis: {len(lab_observations)} lab value(s), "
        f"{len(lab_explanations)} simplified explanation(s)."
    )

    if st.button("Analyze report", type="primary", disabled=not has_source_text):
        try:
            with st.spinner("Extracting lab values and simplifying terminology..."):
                observation_count, explanation_count = run_full_analysis(selected_id, pages)
        except (LabExtractionError, SimplificationError) as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error("Could not complete report analysis.")
            st.code(str(exc))
        else:
            st.success(
                f"Saved {observation_count} lab value(s) and {explanation_count} explanation(s)."
            )
            lab_observations = get_lab_observations(selected_id)
            lab_explanations = get_lab_explanations(selected_id)
    if not has_source_text:
        st.info("This report has no selectable text, so analysis is disabled.")

    with st.expander("Advanced single-step actions"):
        extract_disabled = not has_source_text
        simplify_disabled = not lab_observations
        if st.button("Extract lab values", disabled=extract_disabled):
            try:
                extracted = extract_lab_observations(pages)
                replace_lab_observations(selected_id, extracted)
            except LabExtractionError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error("Could not save extracted lab values.")
                st.code(str(exc))
            else:
                st.success(f"Saved {len(extracted)} lab observation(s).")
                lab_observations = get_lab_observations(selected_id)
                lab_explanations = get_lab_explanations(selected_id)

        if st.button("Simplify lab values", disabled=simplify_disabled):
            try:
                explanations = simplify_lab_observations(lab_observations)
                replace_lab_explanations(selected_id, explanations)
            except SimplificationError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error("Could not save simplified lab explanations.")
                st.code(str(exc))
            else:
                st.success(f"Saved {len(explanations)} simplified explanation(s).")
                lab_explanations = get_lab_explanations(selected_id)

    if lab_observations:
        st.markdown("**Extracted lab values**")
        st.dataframe(observation_table(lab_observations), hide_index=True, use_container_width=True)
    else:
        st.info("No lab values extracted for this report yet.")

    if lab_explanations:
        st.markdown("**Simplified explanations**")
        st.warning(
            "These explanations are educational only and must be checked against the source report with a licensed clinician."
        )
        st.dataframe(explanation_table(lab_explanations), hide_index=True, use_container_width=True)
    elif lab_observations:
        st.info("No simplified explanations saved for this report yet.")

    if pages:
        with st.expander("Stored source text"):
            preview_pages = [
                {"page_number": page["page_number"], "text": page["text_content"]}
                for page in pages
            ]
            st.text_area("Source preview", combined_preview(preview_pages), height=260)
    else:
        st.info("This report has no stored selectable text yet.")


def report_comparison() -> None:
    st.subheader("Compare reports")
    try:
        reports = list_reports()
    except Exception as exc:
        st.error("Could not load reports from PostgreSQL.")
        st.code(str(exc))
        return

    if len(reports) < 2:
        st.info("Upload and analyze at least two reports to compare lab trends.")
        return

    selected_ids = st.multiselect(
        "Reports to compare",
        options=[report["id"] for report in reports],
        default=[report["id"] for report in reports[:2]],
        format_func=lambda report_id: next(
            report["original_filename"] for report in reports if report["id"] == report_id
        ),
    )
    if len(selected_ids) < 2:
        st.info("Select at least two reports.")
        return

    observations = get_lab_observations_for_reports(selected_ids)
    trend_points = build_trend_points(observations)
    repeated_tests = repeated_lab_names(trend_points)

    if not repeated_tests:
        st.info("No repeated numeric lab values found across the selected reports yet.")
        return

    selected_test = st.selectbox("Lab trend", repeated_tests)
    selected_points = [
        point for point in trend_points if point["Normalized test"] == selected_test
    ]
    trend_frame = pd.DataFrame(selected_points)
    summary = summarize_trend(selected_points)
    latest_label = (
        f"{summary['Latest']} {summary.get('Unit', '')}".strip()
        if summary["Latest"] is not None
        else "No data"
    )

    metric_cols = st.columns(3)
    metric_cols[0].metric("Latest", latest_label)
    metric_cols[1].metric("Change", summary["Change"])
    metric_cols[2].metric("Direction", summary["Direction"])

    st.dataframe(trend_frame, hide_index=True, use_container_width=True)

    chart = px.line(
        trend_frame,
        x="Date",
        y="Value",
        markers=True,
        hover_data=["Report", "Test", "Unit", "Reference range", "Flag", "Source page"],
        title=f"{selected_test} trend",
    )
    st.plotly_chart(chart, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Medical Report Simplifier", layout="wide")
    show_app_header()
    show_disclaimer()

    db_ready = initialize_database()
    if not db_ready:
        return

    upload_tab, report_tab, compare_tab = st.tabs(["Upload", "Reports", "Compare"])
    with upload_tab:
        upload_report()
    with report_tab:
        report_history()
    with compare_tab:
        report_comparison()


if __name__ == "__main__":
    main()
