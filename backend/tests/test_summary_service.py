
from app.ai import summary_service
from app.schemas.summary import ClinicalSummary


def sample_bundle():
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-001",
                    "name": [{"given": ["Abebe"], "family": "Kebede"}],
                    "gender": "male",
                    "birthDate": "1990-01-01",
                }
            },
            {
                "resource": {
                    "resourceType": "DiagnosticReport",
                    "id": "report-001",
                    "status": "final",
                    "code": {"text": "Chest X-ray"},
                    "conclusion": "No acute abnormality reported.",
                }
            },
        ],
    }


def sample_llm_response():
    return {
        "patient_id": "patient-001",
        "chief_concern": "Not documented.",
        "diagnoses": [],
        "recent_imaging": ["Chest X-ray: No acute abnormality reported."],
        "recent_labs": [],
        "anomalies": [],
        "summary": "The available record contains a chest X-ray report.",
        "data_completeness": "limited",
        "missing_information": ["No laboratory results were included."],
        "disclaimer": "AI-generated summary. Not a diagnosis.",
    }


class FakeProvider:
    def __init__(self):
        self.calls = 0

    def generate_json(self, *, system_prompt, user_prompt):
        self.calls += 1
        return sample_llm_response()


def test_summary_is_generated_and_cached(monkeypatch):
    provider = FakeProvider()
    saved_summaries = []

    monkeypatch.setattr(
        summary_service,
        "get_bundles_for_patient",
        lambda patient_id: [sample_bundle()],
    )
    monkeypatch.setattr(
        summary_service,
        "get_cached_summary",
        lambda patient_id, records_hash: None,
    )
    monkeypatch.setattr(
        summary_service,
        "save_summary",
        lambda patient_id, records_hash, summary: (
            saved_summaries.append((patient_id, records_hash, summary))
        ),
    )
    monkeypatch.setattr(
        summary_service,
        "get_llm_provider",
        lambda: provider,
    )

    result = summary_service.generate_patient_summary("patient-001")

    assert isinstance(result, ClinicalSummary)
    assert result.patient_id == "patient-001"
    assert provider.calls == 1
    assert len(saved_summaries) == 1
    assert saved_summaries[0][0] == "patient-001"


def test_cached_summary_skips_llm_call(monkeypatch):
    provider = FakeProvider()

    cached_summary = ClinicalSummary.model_validate(
        sample_llm_response()
    )

    monkeypatch.setattr(
        summary_service,
        "get_bundles_for_patient",
        lambda patient_id: [sample_bundle()],
    )
    monkeypatch.setattr(
        summary_service,
        "get_cached_summary",
        lambda patient_id, records_hash: cached_summary,
    )
    monkeypatch.setattr(
        summary_service,
        "get_llm_provider",
        lambda: provider,
    )

    result = summary_service.generate_patient_summary("patient-001")

    assert result == cached_summary
    assert provider.calls == 0


def test_missing_patient_records_raise_error(monkeypatch):
    monkeypatch.setattr(
        summary_service,
        "get_bundles_for_patient",
        lambda patient_id: [],
    )

    try:
        summary_service.generate_patient_summary("missing-patient")
        assert False, "Expected PatientRecordsNotFoundError"
    except summary_service.PatientRecordsNotFoundError:
        pass
