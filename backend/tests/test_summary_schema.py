
import pytest
from pydantic import ValidationError

from app.schemas.summary import ClinicalSummary
from app.ai.mock_provider import MockProvider


def test_valid_summary_is_accepted():
    summary = ClinicalSummary(
        patient_id="patient-123",
        chief_concern="Routine follow-up.",
        diagnoses=["Hypertension"],
        recent_labs=["Blood pressure: 130/85 mmHg"],
        summary="Patient attended a routine follow-up.",
        data_completeness="moderate",
    )

    assert summary.patient_id == "patient-123"
    assert summary.data_completeness == "moderate"


def test_summary_rejects_200_or_more_words():
    with pytest.raises(ValidationError):
        ClinicalSummary(
            patient_id="patient-123",
            summary=" ".join(["clinical"] * 200),
            data_completeness="limited",
        )


def test_summary_rejects_unexpected_fields():
    with pytest.raises(ValidationError):
        ClinicalSummary(
            patient_id="patient-123",
            summary="A short summary.",
            data_completeness="limited",
            unexpected_field="not allowed",
        )


def test_mock_provider_returns_json_dictionary():
    provider = MockProvider()

    result = provider.generate_json(
        system_prompt="Test system prompt",
        user_prompt="Test user prompt",
    )

    assert isinstance(result, dict)
    assert "summary" in result
    assert "data_completeness" in result
