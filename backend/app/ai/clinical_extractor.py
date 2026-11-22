
"""Extract structured clinical context from FHIR R4 Bundles."""
from __future__ import annotations

import base64
import binascii
from datetime import datetime
from typing import Any


def _resource_entries(bundle: dict, resource_type: str) -> list[dict]:
    """Return resources of a given type from a FHIR Bundle."""
    return [
        entry.get("resource", {})
        for entry in bundle.get("entry", [])
        if entry.get("resource", {}).get("resourceType") == resource_type
    ]


def _reference_display(reference: dict | None) -> str | None:
    if not reference:
        return None

    return reference.get("display") or reference.get("reference")


def _extract_patient(bundle: dict) -> dict | None:
    patients = _resource_entries(bundle, "Patient")

    if not patients:
        return None

    patient = patients[0]

    name_parts = []
    for name in patient.get("name", []):
        given = " ".join(name.get("given", []))
        family = name.get("family", "")
        full_name = " ".join(part for part in [given, family] if part)
        if full_name:
            name_parts.append(full_name)

    return {
        "patient_id": patient.get("id"),
        "mrn": next(
            (
                identifier.get("value")
                for identifier in patient.get("identifier", [])
                if identifier.get("value")
            ),
            None,
        ),
        "name": ", ".join(name_parts) or None,
        "gender": patient.get("gender"),
        "birth_date": patient.get("birthDate"),
    }


def _extract_encounters(bundle: dict) -> list[dict]:
    results = []

    for encounter in _resource_entries(bundle, "Encounter"):
        period = encounter.get("period", {})

        results.append({
            "id": encounter.get("id"),
            "status": encounter.get("status"),
            "class": encounter.get("class", {}).get("code"),
            "type": [
                coding.get("display") or coding.get("code")
                for item in encounter.get("type", [])
                for coding in item.get("coding", [])
            ],
            "start": period.get("start"),
            "end": period.get("end"),
            "reason": [
                coding.get("display") or coding.get("code")
                for reason in encounter.get("reasonCode", [])
                for coding in reason.get("coding", [])
            ],
        })

    return results


def _extract_diagnostic_reports(bundle: dict) -> list[dict]:
    results = []

    for report in _resource_entries(bundle, "DiagnosticReport"):
        results.append({
            "id": report.get("id"),
            "status": report.get("status"),
            "code": report.get("code", {}).get("text"),
            "code_codings": [
                coding.get("display") or coding.get("code")
                for coding in report.get("code", {}).get("coding", [])
            ],
            "effective": (
                report.get("effectiveDateTime")
                or report.get("effectivePeriod")
            ),
            "issued": report.get("issued"),
            "conclusion": report.get("conclusion"),
            "conclusion_code": [
                coding.get("display") or coding.get("code")
                for item in report.get("conclusionCode", [])
                for coding in item.get("coding", [])
            ],
            "results": [
                _reference_display(result)
                for result in report.get("result", [])
            ],
        })

    return results


def _extract_document_text(document: dict) -> list[str]:
    """Extract safely decodable text from DocumentReference attachments."""
    extracted = []

    for content in document.get("content", []):
        attachment = content.get("attachment", {})
        data = attachment.get("data")

        if not data:
            continue

        try:
            decoded = base64.b64decode(data, validate=True).decode(
                "utf-8", errors="replace"
            )
        except (ValueError, binascii.Error):
            continue

        if decoded.strip():
            extracted.append(decoded.strip())

    return extracted


def _extract_documents(bundle: dict) -> list[dict]:
    results = []

    for document in _resource_entries(bundle, "DocumentReference"):
        results.append({
            "id": document.get("id"),
            "status": document.get("status"),
            "type": document.get("type", {}).get("text"),
            "type_codings": [
                coding.get("display") or coding.get("code")
                for coding in document.get("type", {}).get("coding", [])
            ],
            "date": document.get("date"),
            "description": document.get("description"),
            "content": _extract_document_text(document),
        })

    return results


def _extract_observations(bundle: dict) -> list[dict]:
    """Extract observations, including laboratory values when present."""
    results = []

    for observation in _resource_entries(bundle, "Observation"):
        value = None

        for key in (
            "valueQuantity",
            "valueString",
            "valueCodeableConcept",
            "valueBoolean",
            "valueInteger",
            "valueRange",
        ):
            if key in observation:
                value = observation[key]
                break

        results.append({
            "id": observation.get("id"),
            "status": observation.get("status"),
            "category": [
                coding.get("display") or coding.get("code")
                for category in observation.get("category", [])
                for coding in category.get("coding", [])
            ],
            "code": observation.get("code", {}).get("text"),
            "code_codings": [
                coding.get("display") or coding.get("code")
                for coding in observation.get("code", {}).get("coding", [])
            ],
            "effective": (
                observation.get("effectiveDateTime")
                or observation.get("effectivePeriod")
            ),
            "value": value,
            "interpretation": [
                coding.get("display") or coding.get("code")
                for item in observation.get("interpretation", [])
                for coding in item.get("coding", [])
            ],
            "reference_range": observation.get("referenceRange", []),
        })

    return results


def extract_clinical_context(bundles: list[dict]) -> dict[str, Any]:
    """Combine clinical resources from all Bundles for one patient."""
    patient = None
    encounters = []
    diagnostic_reports = []
    documents = []
    observations = []

    for bundle in bundles:
        if patient is None:
            patient = _extract_patient(bundle)

        encounters.extend(_extract_encounters(bundle))
        diagnostic_reports.extend(_extract_diagnostic_reports(bundle))
        documents.extend(_extract_documents(bundle))
        observations.extend(_extract_observations(bundle))

    return {
        "patient": patient,
        "encounters": encounters,
        "diagnostic_reports": diagnostic_reports,
        "documents": documents,
        "observations": observations,
    }
