
"""Clinical summarization orchestration service."""
from __future__ import annotations

import hashlib
import json
import logging



from app.ai.clinical_extractor import extract_clinical_context
from app.ai.factory import get_llm_provider
from app.ai.prompts import SYSTEM_PROMPT, build_summary_prompt
from app.ai.summary_storage import get_cached_summary, save_summary
from app.fhir.storage import get_bundles_for_patient
from app.schemas.summary import ClinicalSummary

logger = logging.getLogger(__name__)

class PatientRecordsNotFoundError(Exception):
    """Raised when no FHIR records exist for the requested patient."""


class SummaryGenerationError(Exception):
    """Raised when summary generation or validation fails."""


def _records_hash(clinical_context: dict) -> str:
    """Create a stable hash for the extracted clinical records."""
    serialized = json.dumps(
        clinical_context,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def generate_patient_summary(patient_id: str) -> ClinicalSummary:
    bundles = get_bundles_for_patient(patient_id)

    if not bundles:
        raise PatientRecordsNotFoundError(
            f"No FHIR records found for patient '{patient_id}'."
        )

    clinical_context = extract_clinical_context(bundles)

    if not clinical_context.get("patient"):
        raise PatientRecordsNotFoundError(
            "The stored FHIR Bundles do not contain a Patient resource."
        )

    records_hash = _records_hash(clinical_context)

    # Avoid another LLM request when the records have not changed.
    cached_summary = get_cached_summary(patient_id, records_hash)
    if cached_summary is not None:
        return cached_summary

    try:
        provider = get_llm_provider()

        response = provider.generate_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_summary_prompt(clinical_context),
        )

        if not isinstance(response, dict):
            raise ValueError("The LLM provider did not return a JSON object.")

        response["patient_id"] = patient_id
        response["disclaimer"] = (
            "AI-generated summary of supplied records. "
            "Not a diagnosis or substitute for clinical judgment."
        )

        summary = ClinicalSummary.model_validate(response)

        # Cache only after successful schema validation.
        save_summary(patient_id, records_hash, summary)

        return summary

    except Exception as exc:
        logger.exception("Clinical summary generation failed.")
        raise SummaryGenerationError(
            "Unable to generate or validate the clinical summary."
        ) from exc
