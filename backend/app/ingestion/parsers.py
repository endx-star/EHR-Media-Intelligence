from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from app.config import ALLOWED_EXTENSIONS, MAX_FIELD_CHARS, MAX_RECORDS_PER_FILE


class InputParseError(ValueError):
    """Raised when an input file fails safe parsing or content validation."""


def _validate_record_count(records: list[dict[str, Any]]) -> None:
    if len(records) > MAX_RECORDS_PER_FILE:
        raise InputParseError("File contains more records than the configured limit")


def _validate_field_lengths(records: list[dict[str, Any]]) -> None:
    for record in records:
        for value in record.values():
            if isinstance(value, str) and len(value) > MAX_FIELD_CHARS:
                raise InputParseError("A field exceeds the configured length limit")


def parse_json_text(text: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, RecursionError):
        # Do not return parser excerpts: they may contain patient information.
        raise InputParseError("Invalid JSON document") from None

    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = payload.get("records", [payload])
    else:
        raise InputParseError("JSON root must be an object or an array of objects")

    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise InputParseError("JSON records must be an array of objects")

    _validate_record_count(records)
    _validate_field_lengths(records)
    return records


def parse_csv_text(text: str) -> list[dict[str, Any]]:
    try:
        csv.field_size_limit(MAX_FIELD_CHARS)
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if not reader.fieldnames:
            raise InputParseError("CSV file must contain a header row")

        normalized_headers = [header.strip().casefold() for header in reader.fieldnames]
        if any(not header for header in normalized_headers):
            raise InputParseError("CSV headers must not be empty")
        if len(normalized_headers) != len(set(normalized_headers)):
            raise InputParseError("CSV contains duplicate column headers")

        records: list[dict[str, Any]] = []
        for row in reader:
            # DictReader uses a None key when a row has more cells than headers.
            if None in row:
                raise InputParseError("CSV row contains more columns than the header")
            records.append({key: value for key, value in row.items()})
            if len(records) > MAX_RECORDS_PER_FILE:
                raise InputParseError("File contains more records than the configured limit")

        _validate_field_lengths(records)
        return records
    except (csv.Error, UnicodeError):
        raise InputParseError("Invalid CSV document") from None


def parse_plain_text(text: str) -> list[dict[str, Any]]:
    """Parse a simple key-value clinical note into one record."""
    if not text.strip():
        raise InputParseError("Text file is empty")
    if len(text) > MAX_FIELD_CHARS:
        raise InputParseError("Text file exceeds the configured content limit")

    fields: dict[str, str] = {}
    content_lines: list[str] = []
    known_keys = {
        "mrn": "mrn", "medical record number": "mrn",
        "patient id": "source_patient_id", "source patient id": "source_patient_id",
        "patient name": "full_name", "name": "full_name",
        "dob": "date_of_birth", "date of birth": "date_of_birth",
        "gender": "gender", "sex": "gender",
        "date": "record_date", "record date": "record_date",
        "type": "record_type", "resource type": "record_type",
        "title": "title", "record id": "source_record_id",
    }
    in_content = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if in_content:
            content_lines.append(stripped)
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            normalized_key = key.strip().lower()
            if normalized_key == "content":
                in_content = True
                if value.strip():
                    content_lines.append(value.strip())
            elif normalized_key in known_keys:
                fields[known_keys[normalized_key]] = value.strip()
            else:
                content_lines.append(stripped)
        else:
            content_lines.append(stripped)

    fields["content"] = " ".join(content_lines)
    return [fields]


def parse_file(filename: str, content: bytes) -> tuple[str, list[dict[str, Any]]]:
    """Validate extension, UTF-8 text encoding, and format-specific content."""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise InputParseError("Unsupported file format")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise InputParseError("File must be UTF-8 encoded") from None

    if suffix == ".json":
        return "json", parse_json_text(text)
    if suffix == ".csv":
        return "csv", parse_csv_text(text)
    return "text", parse_plain_text(text)
