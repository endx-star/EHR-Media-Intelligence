
"""SQLite persistence for validated FHIR Bundles."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from app.config import BASE_DIR

DB_PATH = BASE_DIR / "storage" / "fhir_bundles.sqlite3"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fhir_bundles (
            bundle_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            bundle_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fhir_bundles_patient ON fhir_bundles(patient_id)")
    return conn


def save_bundle(bundle: dict) -> None:
    patient_id = next(
        entry["resource"]["id"] for entry in bundle.get("entry", [])
        if entry.get("resource", {}).get("resourceType") == "Patient"
    )
    with _connect() as conn:
        conn.execute(
            """INSERT INTO fhir_bundles(bundle_id, patient_id, bundle_json)
               VALUES (?, ?, ?)
               ON CONFLICT(bundle_id) DO UPDATE SET
                 patient_id=excluded.patient_id, bundle_json=excluded.bundle_json""",
            (bundle["id"], patient_id, json.dumps(bundle, separators=(",", ":"))),
        )


def get_bundles_for_patient(patient_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT bundle_json FROM fhir_bundles WHERE patient_id=? ORDER BY created_at DESC",
            (patient_id,),
        ).fetchall()
    return [json.loads(row[0]) for row in rows]
