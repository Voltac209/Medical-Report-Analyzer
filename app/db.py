from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import psycopg
from psycopg.rows import dict_row

from app.config import get_database_url


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    page_count INTEGER NOT NULL DEFAULT 0,
    text_page_count INTEGER NOT NULL DEFAULT 0,
    text_char_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'uploaded'
);

CREATE TABLE IF NOT EXISTS report_pages (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    text_content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(report_id, page_number)
);

CREATE INDEX IF NOT EXISTS idx_report_pages_report_id
ON report_pages(report_id);

CREATE TABLE IF NOT EXISTS lab_observations (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    test_name TEXT NOT NULL,
    normalized_name TEXT,
    value NUMERIC,
    unit TEXT,
    reference_range TEXT,
    abnormal_flag TEXT,
    report_date TEXT,
    page_number INTEGER,
    source_snippet TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lab_observations_report_id
ON lab_observations(report_id);

CREATE TABLE IF NOT EXISTS lab_explanations (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    test_name TEXT NOT NULL,
    plain_language_name TEXT NOT NULL,
    explanation TEXT NOT NULL,
    result_context TEXT NOT NULL,
    caution TEXT NOT NULL,
    source_page INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lab_explanations_report_id
ON lab_explanations(report_id);
"""

MIGRATION_SQL = """
ALTER TABLE reports
ADD COLUMN IF NOT EXISTS text_page_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE reports
ADD COLUMN IF NOT EXISTS text_char_count INTEGER NOT NULL DEFAULT 0;
"""


@contextmanager
def get_connection():
    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        yield conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(SCHEMA_SQL)
        conn.execute(MIGRATION_SQL)
        conn.commit()


def create_report(
    original_filename: str,
    stored_path: Path,
    page_count: int,
    text_page_count: int,
    text_char_count: int,
    status: str,
) -> int:
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO reports (
                original_filename,
                stored_path,
                page_count,
                text_page_count,
                text_char_count,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                original_filename,
                str(stored_path),
                page_count,
                text_page_count,
                text_char_count,
                status,
            ),
        ).fetchone()
        conn.commit()
        return int(row["id"])


def replace_report_pages(report_id: int, pages: Iterable[dict]) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM report_pages WHERE report_id = %s", (report_id,))
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO report_pages (report_id, page_number, text_content)
                VALUES (%s, %s, %s)
                """,
                [
                    (report_id, page["page_number"], page["text"])
                    for page in pages
                    if page["text"].strip()
                ],
            )
        conn.commit()


def list_reports() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                original_filename,
                stored_path,
                uploaded_at,
                page_count,
                text_page_count,
                text_char_count,
                status
            FROM reports
            ORDER BY uploaded_at DESC
            LIMIT 25
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_report_pages(report_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT page_number, text_content
            FROM report_pages
            WHERE report_id = %s
            ORDER BY page_number
            """,
            (report_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def replace_lab_observations(report_id: int, observations: Iterable[dict]) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM lab_explanations WHERE report_id = %s", (report_id,))
        conn.execute("DELETE FROM lab_observations WHERE report_id = %s", (report_id,))
        rows = [
            (
                report_id,
                observation["test_name"],
                observation.get("normalized_name"),
                observation.get("value"),
                observation.get("unit"),
                observation.get("reference_range"),
                observation.get("abnormal_flag"),
                observation.get("report_date"),
                observation.get("page_number"),
                observation["source_snippet"],
            )
            for observation in observations
        ]
        if rows:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO lab_observations (
                        report_id,
                        test_name,
                        normalized_name,
                        value,
                        unit,
                        reference_range,
                        abnormal_flag,
                        report_date,
                        page_number,
                        source_snippet
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    rows,
                )
        conn.commit()


def get_lab_observations(report_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                test_name,
                normalized_name,
                value,
                unit,
                reference_range,
                abnormal_flag,
                report_date,
                page_number,
                source_snippet
            FROM lab_observations
            WHERE report_id = %s
            ORDER BY test_name, id
            """,
            (report_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_lab_observations_for_reports(report_ids: list[int]) -> list[dict]:
    if not report_ids:
        return []

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                lab_observations.id,
                lab_observations.report_id,
                reports.original_filename,
                reports.uploaded_at,
                lab_observations.test_name,
                lab_observations.normalized_name,
                lab_observations.value,
                lab_observations.unit,
                lab_observations.reference_range,
                lab_observations.abnormal_flag,
                lab_observations.report_date,
                lab_observations.page_number,
                lab_observations.source_snippet
            FROM lab_observations
            JOIN reports ON reports.id = lab_observations.report_id
            WHERE lab_observations.report_id = ANY(%s)
            ORDER BY lab_observations.test_name, reports.uploaded_at
            """,
            (report_ids,),
        ).fetchall()
        return [dict(row) for row in rows]


def replace_lab_explanations(report_id: int, explanations: Iterable[dict]) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM lab_explanations WHERE report_id = %s", (report_id,))
        rows = [
            (
                report_id,
                explanation["test_name"],
                explanation["plain_language_name"],
                explanation["explanation"],
                explanation["result_context"],
                explanation["caution"],
                explanation.get("source_page"),
            )
            for explanation in explanations
        ]
        if rows:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO lab_explanations (
                        report_id,
                        test_name,
                        plain_language_name,
                        explanation,
                        result_context,
                        caution,
                        source_page
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    rows,
                )
        conn.commit()


def get_lab_explanations(report_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                test_name,
                plain_language_name,
                explanation,
                result_context,
                caution,
                source_page
            FROM lab_explanations
            WHERE report_id = %s
            ORDER BY test_name, id
            """,
            (report_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def format_uploaded_at(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%Y-%m-%d %H:%M")
