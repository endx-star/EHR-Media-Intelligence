
"""SQLite persistence for generated clinical summaries."""
from __future__ import annotations

import json
import sqlite3

from app.config import BASE_DIR
from app.schemas.summary import ClinicalSummary


DB_PATH = BASE_DIR / "storage" / "clinical_summaries.sqlite3"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clinical_summaries (
            patient_id TEXT NOT NULL,
            records_hash TEXT NOT NULL,
            summary_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (patient_id, records_hash)
        )
    """)
    return conn


def get_cached_summary(
    patient_id: str,
    records_hash: str,
) -> ClinicalSummary | None:
    """Return a cached summary for this exact version of patient records."""
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT summary_json
            FROM clinical_summaries
            WHERE patient_id = ? AND records_hash = ?
            """,
            (patient_id, records_hash),
        ).fetchone()

    if row is None:
        return None

    return ClinicalSummary.model_validate_json(row[0])


def save_summary(
    patient_id: str,
    records_hash: str,
    summary: ClinicalSummary,
) -> None:
    """Persist a validated summary for the current records hash."""
    summary_json = summary.model_dump_json()

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO clinical_summaries (
                patient_id,
                records_hash,
                summary_json
            )
            VALUES (?, ?, ?)
            ON CONFLICT(patient_id, records_hash)
            DO UPDATE SET
                summary_json = excluded.summary_json,
                created_at = CURRENT_TIMESTAMP
            """,
            (patient_id, records_hash, summary_json),
        )
