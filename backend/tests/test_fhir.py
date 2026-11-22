
from app.ingestion.cleaner import build_report
from app.fhir.bundle import build_patient_bundles
from app.fhir.mapper import patient_key
from app.fhir.validator import validate_bundle
import app.fhir.validator as fhir_validator

def sample_records():
    report = build_report([
        {"record_id": "LAB-1", "patient_id": "SRC-1", "mrn": "000123",
         "patient_name": "Jane Doe", "dob": "1980-02-03", "gender": "F",
         "date": "2026-11-20", "type": "lab", "title": "CBC",
         "content": "Hemoglobin 11.2 g/dL"},
        {"record_id": "NOTE-1", "patient_id": "SRC-1", "mrn": "000123",
         "patient_name": "Jane Doe", "dob": "1980-02-03", "gender": "F",
         "date": "2026-11-21", "type": "discharge summary", "title": "Discharge",
         "content": "Discharged home in stable condition"},
    ], "json")
    return report.records


def test_builds_one_bundle_per_patient_with_required_resource_types():
    bundles = build_patient_bundles(sample_records())
    assert len(bundles) == 1
    types = [entry["resource"]["resourceType"] for entry in bundles[0]["entry"]]
    assert types.count("Patient") == 1
    assert types.count("Encounter") == 2
    assert types.count("DiagnosticReport") == 1
    assert types.count("DocumentReference") == 1


def test_all_internal_references_resolve_inside_bundle(monkeypatch):
    monkeypatch.setattr(
        fhir_validator,
        "_run_hl7_validator",
        lambda bundle: None,
    )

    bundle = build_patient_bundles(sample_records())[0]
    validated = validate_bundle(bundle)

    resources = {
        entry["resource"]["resourceType"]: entry["resource"]
        for entry in validated["entry"]
    }

    patient_id = resources["Patient"]["id"]

    assert (
        resources["DiagnosticReport"]["subject"]["reference"]
        == f"Patient/{patient_id}"
    )

    assert (
        resources["DiagnosticReport"]["encounter"]["reference"]
        .startswith("Encounter/")
    )

    assert (
        resources["DocumentReference"]["context"]["encounter"][0]["reference"]
        .startswith("Encounter/")
    )


def test_conflicting_patient_identities_are_not_merged():
    report = build_report([
        {"mrn": "0001", "patient_id": "SRC-A", "patient_name": "Jane Doe", "content": "note A"},
        {"mrn": "0001", "patient_id": "SRC-B", "patient_name": "Jane Doe", "content": "note B"},
    ], "json")
    assert all(r.identity_conflict for r in report.records)
    assert patient_key(report.records[0]) != patient_key(report.records[1])
    assert len(build_patient_bundles(report.records)) == 2
