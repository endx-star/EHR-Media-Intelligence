
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from app.models.clinical_record import IngestionReport
from app.fhir.service import normalize_and_store
from app.fhir.storage import get_bundles_for_patient
from app.fhir.validator import FHIRValidationError

router = APIRouter(prefix="/fhir", tags=["FHIR R4"])


@router.post("/normalize")
def normalize_ingestion_report(report: IngestionReport):
    """Convert a Task 1 ingestion report into validated, stored FHIR R4 Bundles."""
    if not report.records:
        raise HTTPException(status_code=400, detail="No accepted clinical records were supplied")
    try:
        bundles = normalize_and_store(report.records)
    except FHIRValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception:
        # Do not return internal exception details or clinical values to clients.
        raise HTTPException(status_code=500, detail="FHIR normalization failed") from None
    return {
        "patients_processed": len(bundles),
        "bundles": bundles,
    }


@router.get("/bundles/{patient_id}")
def retrieve_patient_bundles(patient_id: str):
    bundles = get_bundles_for_patient(patient_id)
    if not bundles:
        raise HTTPException(status_code=404, detail="No FHIR Bundles found for this patient")
    return {"patient_id": patient_id, "bundles": bundles}
