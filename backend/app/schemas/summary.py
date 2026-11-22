
"""Pydantic schemas for AI-generated clinical summaries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ClinicalSummary(BaseModel):
    """Validated, structured summary of a patient's FHIR records."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    patient_id: str = Field(min_length=1)
    chief_concern: str = Field(
        default="Not documented",
        max_length=2000,
    )
    diagnoses: list[str] = Field(default_factory=list)
    recent_imaging: list[str] = Field(default_factory=list)
    recent_labs: list[str] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)

    summary: str = Field(min_length=1, max_length=5000)

    # Describes source-data completeness, not diagnostic certainty.
    data_completeness: Literal["limited", "moderate", "good"]
    missing_information: list[str] = Field(default_factory=list)

    disclaimer: str = (
        "AI-generated summary for informational purposes only. "
        "Not a clinical decision or substitute for professional review."
    )

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator(
        "diagnoses",
        "recent_imaging",
        "recent_labs",
        "anomalies",
        "missing_information",
    )
    @classmethod
    def clean_list_items(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]

    @model_validator(mode="after")
    def enforce_word_limit(self) -> "ClinicalSummary":
        """Keep the complete clinical summary under 200 words."""

        text_parts = [
            self.chief_concern,
            *self.diagnoses,
            *self.recent_imaging,
            *self.recent_labs,
            *self.anomalies,
            self.summary,
            *self.missing_information,
        ]

        word_count = len(" ".join(text_parts).split())

        if word_count >= 200:
            raise ValueError(
                f"Clinical summary must contain fewer than 200 words; "
                f"received {word_count}."
            )

        return self
