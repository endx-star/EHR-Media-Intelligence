
"""Deterministic mock provider for development and automated tests."""

from __future__ import annotations

from typing import Any

from app.ai.base import BaseLLMProvider


class MockProvider(BaseLLMProvider):
    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        return {
            "patient_id": "mock-patient",
            "chief_concern": "Clinical follow-up documented.",
            "diagnoses": [],
            "recent_imaging": [],
            "recent_labs": [
                "Hemoglobin: 11.2 g/dL (source value; interpretation requires clinical context)."
            ],
            "anomalies": [],
            "summary": (
                "The available records contain a clinical follow-up "
                "and a laboratory result. No additional diagnoses or "
                "imaging findings were supplied in this mock response."
            ),
            "data_completeness": "limited",
            "missing_information": [
                "Additional clinical history was not supplied."
            ],
            "disclaimer": (
                "AI-generated summary for informational purposes only. "
                "Not a clinical decision or substitute for professional review."
            ),
        }
