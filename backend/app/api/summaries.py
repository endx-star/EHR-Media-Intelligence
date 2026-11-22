
"""API endpoints for AI-generated clinical summaries."""
from fastapi import APIRouter, HTTPException, Path, status

from app.ai.summary_service import (
    PatientRecordsNotFoundError,
    SummaryGenerationError,
    generate_patient_summary,
)
from app.schemas.summary import ClinicalSummary


router = APIRouter(
    prefix="/api/v1/summaries",
    tags=["Clinical Summaries"],
)


@router.post(
    "/{patient_id}",
    response_model=ClinicalSummary,
    status_code=status.HTTP_200_OK,
    summary="Generate or retrieve a clinical summary",
    description=(
        "Generates a summary from stored synthetic FHIR records. "
        "Returns a cached summary when the underlying records are unchanged."
    ),
)
def create_patient_summary(
    patient_id: str = Path(min_length=1, max_length=128),
) -> ClinicalSummary:
    try:
        return generate_patient_summary(patient_id)

    except PatientRecordsNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except SummaryGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
