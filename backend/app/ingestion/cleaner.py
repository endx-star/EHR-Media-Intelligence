from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Any

from dateutil import parser as date_parser
from pydantic import ValidationError

from app.models.clinical_record import (
    AuditEntry, CleanClinicalRecord, Gender, IngestionReport,
    PatientIdentity, ResourceType,
)


GENDER_MAP = {
    "m": Gender.MALE, "male": Gender.MALE, "man": Gender.MALE,
    "f": Gender.FEMALE, "female": Gender.FEMALE, "woman": Gender.FEMALE,
    "o": Gender.OTHER, "other": Gender.OTHER, "non-binary": Gender.OTHER,
    "nonbinary": Gender.OTHER,
    "u": Gender.UNKNOWN, "unk": Gender.UNKNOWN, "unknown": Gender.UNKNOWN,
    "": Gender.UNKNOWN, "none": Gender.UNKNOWN, "null": Gender.UNKNOWN,
}


def _value(raw: dict[str, Any], *keys: str) -> Any:
    lowered = {str(k).strip().lower(): v for k, v in raw.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value is not None and str(value).strip() != "":
            return value
    return None


def _audit(action: str, field: str | None, reason: str) -> AuditEntry:
    """Create an audit event without storing raw or transformed patient values."""
    return AuditEntry(action=action, field=field, reason=reason)


def normalize_mrn(value: Any) -> str | None:
    if value is None:
        return None
    # Keep leading zeroes; remove spaces and common display separators only.
    normalized = re.sub(r"[\s-]+", "", str(value)).upper()
    return normalized or None


def normalize_date(value: Any) -> date | None:
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = date_parser.parse(str(value), fuzzy=False, dayfirst=False)
    return parsed.date()


def normalize_gender(value: Any) -> Gender:
    if value is None:
        return Gender.UNKNOWN
    return GENDER_MAP.get(str(value).strip().lower(), Gender.UNKNOWN)


def normalize_resource_type(value: Any) -> ResourceType:
    normalized = str(value or "document").strip().lower().replace("_", "").replace(" ", "")
    if normalized in {"diagnosticreport", "lab", "laboratory", "result", "imagingreport"}:
        return ResourceType.DIAGNOSTIC_REPORT
    if normalized in {"documentreference", "document", "note", "discharge", "dischargesummary", "imaging"}:
        return ResourceType.DOCUMENT_REFERENCE
    return ResourceType.OTHER


def _record_hash(record: CleanClinicalRecord) -> str:
    identity = record.patient.mrn or record.patient.source_patient_id or (record.patient.full_name or "unknown").lower()
    material = "|".join([
        identity, str(record.record_date or ""), record.resource_type.value,
        record.title.casefold(), record.content.casefold(),
    ])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def clean_one(raw: dict[str, Any], source_format: str) -> CleanClinicalRecord:
    audit: list[AuditEntry] = []

    raw_mrn = _value(raw, "mrn", "medical_record_number", "medical record number")
    mrn = normalize_mrn(raw_mrn)
    if raw_mrn is not None and mrn != str(raw_mrn).strip():
        audit.append(_audit("normalized", "patient.mrn", "Removed MRN display separators and standardized case"))
    elif raw_mrn is None:
        audit.append(_audit("missing", "patient.mrn", "No medical record number was supplied"))

    raw_dob = _value(raw, "date_of_birth", "dob", "birth_date")
    try:
        dob = normalize_date(raw_dob)
        if raw_dob is not None and dob is not None and str(raw_dob) != dob.isoformat():
            audit.append(_audit("normalized", "patient.date_of_birth", "Normalized date to ISO-8601"))
    except (ValueError, OverflowError) as exc:
        dob = None
        audit.append(_audit("rejected_value", "patient.date_of_birth", "Source date could not be parsed"))

    raw_record_date = _value(raw, "record_date", "date", "document_date", "result_date", "performed_date")
    try:
        record_date = normalize_date(raw_record_date)
        if raw_record_date is not None and record_date is not None and str(raw_record_date) != record_date.isoformat():
            audit.append(_audit("normalized", "record_date", "Normalized date to ISO-8601"))
    except (ValueError, OverflowError) as exc:
        record_date = None
        audit.append(_audit("rejected_value", "record_date", "Source date could not be parsed"))

    raw_gender = _value(raw, "gender", "sex")
    gender = normalize_gender(raw_gender)
    if raw_gender is None:
        audit.append(_audit("defaulted", "patient.gender", "Missing gender represented as unknown"))
    elif str(raw_gender).strip().lower() != gender.value:
        audit.append(_audit("normalized", "patient.gender", "Mapped source gender code to canonical value"))

    raw_name = _value(raw, "full_name", "patient_name", "patient name", "name")
    if raw_name is None:
        audit.append(_audit("missing", "patient.full_name", "Patient name was not supplied"))

    source_patient_id = _value(raw, "source_patient_id", "patient_id", "patient id", "sourcepatientid")
    if source_patient_id is None:
        audit.append(_audit("missing", "patient.source_patient_id", "No source patient identifier was supplied"))
    source_record_id = _value(raw, "source_record_id", "record_id", "document_id", "id")
    title = _value(raw, "title", "document_title", "test_name", "name") or "Untitled clinical record"
    content = _value(raw, "content", "text", "note", "description", "result", "report") or ""
    if not str(content).strip():
        audit.append(_audit("missing", "content", "No clinical text was supplied"))

    patient = PatientIdentity(
        source_patient_id=str(source_patient_id).strip() if source_patient_id is not None else None,
        mrn=mrn,
        full_name=str(raw_name).strip() if raw_name is not None else None,
        date_of_birth=dob,
        gender=gender,
    )
    return CleanClinicalRecord(
        source_record_id=str(source_record_id).strip() if source_record_id is not None else None,
        patient=patient,
        record_date=record_date,
        resource_type=normalize_resource_type(_value(raw, "resource_type", "record_type", "type")),
        title=str(title).strip(),
        content=str(content),
        source_format=source_format,
        audit_log=audit,
    )


def build_report(raw_records: list[dict[str, Any]], source_format: str) -> IngestionReport:
    accepted: list[CleanClinicalRecord] = []
    rejected = 0
    duplicate_count = 0
    errors: list[str] = []
    batch_audit: list[AuditEntry] = []
    seen_hashes: set[str] = set()
    identity_map: dict[str, dict[str, set[str]]] = {}
    conflicting_mrns: set[str] = set()
    source_id_to_mrns: dict[str, set[str]] = {}

    for index, raw in enumerate(raw_records):
        try:
            record = clean_one(raw, source_format)
        except (ValidationError, TypeError, ValueError) as exc:
            rejected += 1
            # Never echo rejected values or raw validation exceptions; they may contain PHI.
            errors.append(f"Record {index + 1}: record_validation_failed")
            continue

        # Detect identity collisions. Do not merge or discard; flag for review.
        patient = record.patient
        if patient.source_patient_id and patient.mrn:
            source_id_to_mrns.setdefault(patient.source_patient_id, set()).add(patient.mrn)
        if patient.mrn:
            slot = identity_map.setdefault(patient.mrn, {"source_ids": set(), "names": set()})
            if patient.source_patient_id:
                slot["source_ids"].add(patient.source_patient_id)
            if patient.full_name:
                slot["names"].add(patient.full_name.casefold())
            if len(slot["source_ids"]) > 1 or len(slot["names"]) > 1:
                conflicting_mrns.add(patient.mrn)

        digest = _record_hash(record)
        if digest in seen_hashes:
            duplicate_count += 1
            batch_audit.append(_audit("duplicate_skipped", None, f"Duplicate record skipped at input position {index + 1}"))
            continue
        seen_hashes.add(digest)
        accepted.append(record)

    # A source patient ID must not point to multiple MRNs either.
    for source_id, mrns in source_id_to_mrns.items():
        if len(mrns) > 1:
            conflicting_mrns.update(mrns)

    # Mark every record associated with a conflicting MRN, including earlier records.
    for record in accepted:
        if record.patient.mrn in conflicting_mrns:
            record.identity_conflict = True
            slot = identity_map[record.patient.mrn]
            if len(slot["source_ids"]) > 1:
                warning = "The same MRN is associated with multiple source patient IDs; manual identity review required."
                if warning not in record.warnings:
                    record.warnings.append(warning)
            if len(slot["names"]) > 1:
                warning = "The same MRN is associated with different patient names; manual identity review required."
                if warning not in record.warnings:
                    record.warnings.append(warning)
            if record.patient.source_patient_id and len(source_id_to_mrns.get(record.patient.source_patient_id, set())) > 1:
                warning = "The same source patient ID is associated with multiple MRNs; manual identity review required."
                if warning not in record.warnings:
                    record.warnings.append(warning)
    conflicts = sum(1 for record in accepted if record.identity_conflict)
    return IngestionReport(
        total_input_records=len(raw_records),
        accepted_records=len(accepted),
        duplicate_records=duplicate_count,
        rejected_records=rejected,
        identity_conflicts=conflicts,
        records=accepted,
        batch_audit=batch_audit,
        errors=errors,
    )
