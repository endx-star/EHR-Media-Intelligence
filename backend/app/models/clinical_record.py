from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class ResourceType(str, Enum):
    DOCUMENT_REFERENCE = "DocumentReference"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    OTHER = "Other"


class AuditEntry(BaseModel):
    """Non-content audit event; never stores patient values or clinical text."""

    model_config = ConfigDict(extra="forbid")

    action: str
    field: str | None = None
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PatientIdentity(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    source_patient_id: str | None = None
    mrn: str | None = None
    full_name: str | None = None
    date_of_birth: date | None = None
    gender: Gender = Gender.UNKNOWN


class CleanClinicalRecord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    source_record_id: str | None = None
    patient: PatientIdentity
    record_date: date | None = None
    resource_type: ResourceType = ResourceType.DOCUMENT_REFERENCE
    title: str = "Untitled clinical record"
    content: str = ""
    source_format: str
    identity_conflict: bool = False
    warnings: list[str] = Field(default_factory=list)
    audit_log: list[AuditEntry] = Field(default_factory=list)

    @field_validator("content")
    @classmethod
    def normalize_content_whitespace(cls, value: str) -> str:
        return " ".join(value.split())


class IngestionReport(BaseModel):
    total_input_records: int
    accepted_records: int
    duplicate_records: int
    rejected_records: int
    identity_conflicts: int
    records: list[CleanClinicalRecord]
    batch_audit: list[AuditEntry] = Field(default_factory=list)
    # Errors contain record position and a generic code only, never raw values.
    errors: list[str] = Field(default_factory=list)
