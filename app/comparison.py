from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import re
from typing import Any


NORMALIZED_NAME_ALIASES = {
    "a1c": "hba1c",
    "hb a1c": "hba1c",
    "hba1c": "hba1c",
    "hemoglobin a1c": "hba1c",
    "haemoglobin a1c": "hba1c",
    "hemoglobin": "hemoglobin",
    "haemoglobin": "hemoglobin",
    "total cholesterol": "cholesterol total",
}


def normalize_lab_name(name: str | None) -> str:
    if not name:
        return ""
    cleaned = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    return NORMALIZED_NAME_ALIASES.get(cleaned, cleaned)


def numeric_value(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def trend_date(observation: dict) -> str:
    report_date = observation.get("report_date")
    if report_date:
        return str(report_date)
    uploaded_at = observation.get("uploaded_at")
    if isinstance(uploaded_at, datetime):
        return uploaded_at.strftime("%Y-%m-%d")
    return ""


def build_trend_points(observations: list[dict]) -> list[dict]:
    trend_points = []
    for observation in observations:
        value = numeric_value(observation.get("value"))
        if value is None:
            continue

        normalized_name = normalize_lab_name(
            observation.get("normalized_name") or observation.get("test_name")
        )
        if not normalized_name:
            continue

        trend_points.append(
            {
                "Report ID": observation["report_id"],
                "Report": observation["original_filename"],
                "Test": observation["test_name"],
                "Normalized test": normalized_name,
                "Value": value,
                "Unit": observation.get("unit") or "",
                "Reference range": observation.get("reference_range") or "",
                "Flag": observation.get("abnormal_flag") or "",
                "Date": trend_date(observation),
                "Source page": observation.get("page_number"),
                "Source": observation.get("source_snippet") or "",
            }
        )
    return trend_points


def repeated_lab_names(trend_points: list[dict]) -> list[str]:
    report_ids_by_test: dict[str, set[int]] = defaultdict(set)
    for point in trend_points:
        report_ids_by_test[point["Normalized test"]].add(point["Report ID"])
    return sorted(
        test_name
        for test_name, report_ids in report_ids_by_test.items()
        if len(report_ids) >= 2
    )
