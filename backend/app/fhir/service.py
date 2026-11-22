
from app.fhir.bundle import build_patient_bundles
from app.fhir.validator import validate_bundle
from app.fhir.storage import save_bundle


def normalize_and_store(records):
    bundles = build_patient_bundles(records)
    validated = [validate_bundle(bundle) for bundle in bundles]
    for bundle in validated:
        save_bundle(bundle)
    return validated
