"""Convert stored FHIR R4 resources into searchable clinical documents."""
from __future__ import annotations

import base64
import binascii
import hashlib
from typing import Any
from datetime import date

SEARCHABLE_RESOURCE_TYPES = {"DiagnosticReport", "DocumentReference", "Observation"}


def _resources(bundle: dict, resource_type: str) -> list[dict]:
    return [
        entry.get("resource", {})
        for entry in bundle.get("entry", [])
        if entry.get("resource", {}).get("resourceType") == resource_type
    ]


def _patient_metadata(bundle: dict) -> tuple[str, str | None, str | None]:
    patient = next(iter(_resources(bundle, "Patient")), {})
    patient_id = str(patient.get("id") or "")
    names = patient.get("name", [])
    patient_name = next(
        (name.get("text") for name in names if name.get("text")),
        None,
    )
    if patient_name is None and names:
        first = names[0]
        parts = first.get("given", []) + ([first["family"]] if first.get("family") else [])
        patient_name = " ".join(str(part) for part in parts) or None

    mrn = None
    for identifier in patient.get("identifier", []):
        system = str(identifier.get("system") or "")
        if system.endswith("/identifier/mrn") or not system:
            mrn = identifier.get("value")
            if mrn:
                break
    return patient_id, patient_name, str(mrn) if mrn else None


def _coding_text(concept: dict | None) -> list[str]:
    if not concept:
        return []
    values = []
    if concept.get("text"):
        values.append(str(concept["text"]))
    for coding in concept.get("coding", []):
        display = coding.get("display") or coding.get("code")
        if display:
            values.append(str(display))
    return values


def _date_value(resource: dict, resource_type: str) -> str | None:
    value = (
        resource.get("effectiveDateTime")
        or resource.get("issued")
        or resource.get("date")
    )
    if isinstance(value, dict):
        value = value.get("start")
    if not value and resource_type == "DiagnosticReport":
        period = resource.get("effectivePeriod") or {}
        value = period.get("start")
    if not value:
        return None
    return str(value)[:10]


def _document_reference_text(resource: dict) -> str:
    sections = []
    if resource.get("description"):
        sections.append(str(resource["description"]))

    for content in resource.get("content", []):
        attachment = content.get("attachment", {})
        title = attachment.get("title")
        if title:
            sections.append(str(title))
        content_type = str(attachment.get("contentType") or "").lower()
        encoded = attachment.get("data")
        # This MVP indexes text attachments only. PDF/image OCR is outside scope.
        if encoded and (content_type.startswith("text/") or content_type == "application/json"):
            try:
                decoded = base64.b64decode(encoded, validate=True).decode(
                    "utf-8", errors="replace"
                )
            except (ValueError, binascii.Error):
                continue
            if decoded.strip():
                sections.append(decoded.strip())

    return "\n".join(dict.fromkeys(sections)).strip()


def _resource_document(
    bundle: dict,
    resource: dict,
    patient_id: str,
    patient_name: str | None,
    mrn: str | None,
) -> dict | None:
    resource_type = resource.get("resourceType")
    title = "Clinical record"
    content = ""

    if resource_type == "DiagnosticReport":
        title_parts = _coding_text(resource.get("code"))
        title = title_parts[0] if title_parts else "Diagnostic report"
        content_parts = title_parts.copy()
        if resource.get("conclusion"):
            content_parts.append(str(resource["conclusion"]))
        content = "\n".join(dict.fromkeys(content_parts)).strip()

    elif resource_type == "DocumentReference":
        title_parts = _coding_text(resource.get("type"))
        title = title_parts[0] if title_parts else "Clinical document"
        content = _document_reference_text(resource)
        if not content:
            content = title

    elif resource_type == "Observation":
        title_parts = _coding_text(resource.get("code"))
        title = title_parts[0] if title_parts else "Observation"
        value = None
        for key in (
            "valueQuantity", "valueString", "valueCodeableConcept",
            "valueBoolean", "valueInteger", "valueRange",
        ):
            if key in resource:
                value = resource[key]
                break
        pieces = title_parts.copy()
        if value is not None:
            if isinstance(value, dict) and "value" in value:
                quantity = " ".join(
                    str(part) for part in (
                        value.get("value"), value.get("unit") or value.get("code")
                    ) if part is not None
                )
                pieces.append(quantity)
            elif isinstance(value, dict):
                pieces.append(str(value.get("text") or value))
            else:
                pieces.append(str(value))
        for interpretation in resource.get("interpretation", []):
            pieces.extend(_coding_text(interpretation))
        content = "\n".join(pieces).strip()

    if not patient_id or not content.strip():
        return None

    resource_id = str(resource.get("id") or "")
    bundle_id = str(bundle.get("id") or "")
    stable_material = "|".join([bundle_id, resource_type or "", resource_id])
    document_id = hashlib.sha256(stable_material.encode("utf-8")).hexdigest()

    searchable_text = (
        content if content.casefold().startswith(title.casefold())
        else f"{title}\n{content}"
    )
    record_date = _date_value(resource, resource_type)

    return {
        "id": document_id,
        "document": searchable_text.strip(),
        "metadata": {
             "patient_id": patient_id,
             "patient_name": patient_name or "",
             "mrn": mrn or "",
             "resource_type": resource_type,
             "resource_id": resource_id,
             "bundle_id": bundle_id,
             "record_date": record_date or "",
             "record_date_sort": _date_sort_value(record_date),
             "title": title[:500],
       },
    }


def build_search_documents(bundles: list[dict]) -> list[dict[str, Any]]:
    """Build deterministic, Chroma-compatible documents and scalar metadata."""
    documents = []
    for bundle in bundles:
        patient_id, patient_name, mrn = _patient_metadata(bundle)
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            if resource.get("resourceType") not in SEARCHABLE_RESOURCE_TYPES:
                continue
            document = _resource_document(
                bundle, resource, patient_id, patient_name, mrn
            )
            if document:
                documents.append(document)
    return documents


def _date_sort_value(value: str | None) -> int:
    """Convert an ISO date string into a numeric value for ChromaDB filtering."""
    if not value:
        return 0

    try:
        return date.fromisoformat(value[:10]).toordinal()
    except ValueError:
        return 0