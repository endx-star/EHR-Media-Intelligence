
"""Create one FHIR R4 collection Bundle per patient."""
from __future__ import annotations
from collections import OrderedDict
from typing import Any
from app.models.clinical_record import CleanClinicalRecord, ResourceType
from app.fhir.mapper import (
    map_patient, map_encounter, map_document_reference, map_diagnostic_report,
    patient_key, stable_id, FHIR_BASE,
)


def build_patient_bundles(records: list[CleanClinicalRecord]) -> list[dict[str, Any]]:
    grouped: OrderedDict[str, list[CleanClinicalRecord]] = OrderedDict()
    for record in records:
        grouped.setdefault(patient_key(record), []).append(record)

    bundles = []
    for pkey, patient_records in grouped.items():
        entries: list[dict[str, Any]] = []
        patient = map_patient(patient_records[0])
        entries.append({"fullUrl": f"{FHIR_BASE}/Patient/{pkey}", "resource": patient})
        for record in patient_records:
            encounter = map_encounter(record)
            entries.append({"fullUrl": f"{FHIR_BASE}/Encounter/{encounter['id']}", "resource": encounter})
            if record.resource_type == ResourceType.DIAGNOSTIC_REPORT:
                clinical = map_diagnostic_report(record, encounter["id"])
            else:
                # Unknown source types are retained as source documents rather than dropped.
                clinical = map_document_reference(record, encounter["id"])
            entries.append({"fullUrl": f"{FHIR_BASE}/{clinical['resourceType']}/{clinical['id']}", "resource": clinical})
        bundle_id = stable_id("bundle", pkey, *[str(r.source_record_id or r.title) for r in patient_records])
        bundles.append({
            "resourceType": "Bundle",
            "id": bundle_id,
            "type": "collection",
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z"),
            "entry": entries,
        })
    return bundles
