
"""Map cleaned clinical records into FHIR R4 resources."""
from __future__ import annotations
import hashlib
import base64
from datetime import datetime, timezone
from typing import Any
from app.models.clinical_record import CleanClinicalRecord, ResourceType

FHIR_BASE = "https://ehr-media-intelligence.example/fhir"


def stable_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


def patient_key(record: CleanClinicalRecord) -> str:
    p = record.patient
    if record.identity_conflict:
        # Never merge records flagged by Task 1 as identity collisions.
        identity = "|".join([
            "conflict", p.mrn or "", p.source_patient_id or "",
            (p.full_name or "").casefold(), str(p.date_of_birth or ""),
        ])
    else:
        identity = p.mrn or p.source_patient_id or (
            (p.full_name or "unknown").casefold() + "|" + str(p.date_of_birth or "")
        )
    return stable_id("patient", identity)


def map_patient(record: CleanClinicalRecord) -> dict[str, Any]:
    p = record.patient
    resource: dict[str, Any] = {
        "resourceType": "Patient",
        "id": patient_key(record),
        "active": True,
        "gender": p.gender.value,
    }
    if p.full_name:
        resource["name"] = [{"text": p.full_name}]
    if p.date_of_birth:
        resource["birthDate"] = p.date_of_birth.isoformat()
    identifiers = []
    if p.mrn:
        identifiers.append({"system": f"{FHIR_BASE}/identifier/mrn", "value": p.mrn})
    if p.source_patient_id:
        identifiers.append({"system": f"{FHIR_BASE}/identifier/source-patient-id", "value": p.source_patient_id})
    if identifiers:
        resource["identifier"] = identifiers
    return resource


def map_encounter(record: CleanClinicalRecord) -> dict[str, Any]:
    encounter_id = stable_id("encounter", patient_key(record), record.source_record_id or "",
                             str(record.record_date or ""), record.title, record.content)
    resource: dict[str, Any] = {
        "resourceType": "Encounter",
        "id": encounter_id,
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                  "code": "AMB", "display": "ambulatory"},
        "subject": {"reference": f"Patient/{patient_key(record)}"},
    }
    if record.record_date:
        resource["period"] = {
            "start": datetime.combine(record.record_date, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        }
    return resource


def map_document_reference(record: CleanClinicalRecord, encounter_id: str) -> dict[str, Any]:
    rid = stable_id("document", patient_key(record), record.source_record_id or "",
                    str(record.record_date or ""), record.title, record.content)
    resource: dict[str, Any] = {
        "resourceType": "DocumentReference",
        "id": rid,
        "status": "current",
        "subject": {"reference": f"Patient/{patient_key(record)}"},
        "type": {"text": record.title},
        "content": [{"attachment": {
            "contentType": "text/plain",
            "data": base64.b64encode(record.content.encode("utf-8")).decode("ascii"),
            "title": record.title,
        }}],
        "context": {"encounter": [{"reference": f"Encounter/{encounter_id}"}]},
    }
    if record.record_date:
        resource["date"] = datetime.combine(record.record_date, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return resource


def map_diagnostic_report(record: CleanClinicalRecord, encounter_id: str) -> dict[str, Any]:
    rid = stable_id("diagnostic-report", patient_key(record), record.source_record_id or "",
                    str(record.record_date or ""), record.title, record.content)
    resource: dict[str, Any] = {
        "resourceType": "DiagnosticReport",
        "id": rid,
        "status": "final",
        "code": {"text": record.title},
        "subject": {"reference": f"Patient/{patient_key(record)}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"},
        "conclusion": record.content,
    }
    if record.record_date:
        resource["effectiveDateTime"] = record.record_date.isoformat()
    return resource
