
from app.ai import summary_storage
from app.schemas.summary import ClinicalSummary


def make_summary() -> ClinicalSummary:
    return ClinicalSummary(
        patient_id="patient-001",
        chief_concern="Routine follow-up.",
        diagnoses=["Hypertension"],
        recent_imaging=[],
        recent_labs=["Hemoglobin: 13.5 g/dL"],
        anomalies=[],
        summary="Patient attended a routine follow-up.",
        data_completeness="good",
        missing_information=[],
        disclaimer="AI-generated summary. Not a diagnosis.",
    )


def test_save_and_retrieve_cached_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(
        summary_storage,
        "DB_PATH",
        tmp_path / "test_summaries.sqlite3",
    )

    summary = make_summary()

    summary_storage.save_summary(
        "patient-001",
        "hash-001",
        summary,
    )

    cached = summary_storage.get_cached_summary(
        "patient-001",
        "hash-001",
    )

    assert cached is not None
    assert cached.patient_id == "patient-001"
    assert cached.summary == summary.summary


def test_cache_miss_for_different_records_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(
        summary_storage,
        "DB_PATH",
        tmp_path / "test_summaries.sqlite3",
    )

    summary_storage.save_summary(
        "patient-001",
        "hash-001",
        make_summary(),
    )

    cached = summary_storage.get_cached_summary(
        "patient-001",
        "hash-002",
    )

    assert cached is None
