"""Request and response schemas for semantic search."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.config import SEARCH_DEFAULT_TOP_K, SEARCH_MAX_TOP_K


SearchResourceType = Literal[
    "DiagnosticReport",
    "DocumentReference",
    "Observation",
]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=SEARCH_DEFAULT_TOP_K, ge=1, le=SEARCH_MAX_TOP_K)
    resource_type: SearchResourceType | None = None
    date_from: date | None = None
    date_to: date | None = None
    patient_id: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not be later than date_to")
        return self


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: str
    patient_name: str | None = None
    mrn: str | None = None
    resource_type: str
    resource_id: str
    record_date: str | None = None
    title: str
    snippet: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total_results: int
    search_time_ms: float
