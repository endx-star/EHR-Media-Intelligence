
from app.ai.clinical_extractor import extract_clinical_context


def test_extract_patient_and_diagnostic_report():
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-001",
                    "name": [{"given": ["Abebe"], "family": "Kebede"}],
                    "gender": "male",
                    "birthDate": "1990-01-01",
                    "identifier": [{"value": "MRN-001"}],
                }
            },
            {
                "resource": {
                    "resourceType": "DiagnosticReport",
                    "id": "report-001",
                    "status": "final",
                    "code": {"text": "Chest X-ray"},
                    "conclusion": "No acute cardiopulmonary abnormality.",
                }
            },
        ],
    }

    result = extract_clinical_context([bundle])

    assert result["patient"]["patient_id"] == "patient-001"
    assert result["patient"]["name"] == "Abebe Kebede"
    assert result["patient"]["mrn"] == "MRN-001"
    assert result["diagnostic_reports"][0]["code"] == "Chest X-ray"


def test_missing_resources_return_empty_lists():
    result = extract_clinical_context([
        {"resourceType": "Bundle", "entry": []}
    ])

    assert result["patient"] is None
    assert result["encounters"] == []
    assert result["diagnostic_reports"] == []
    assert result["documents"] == []
    assert result["observations"] == []


def test_extract_observation_value():
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-001",
                    "status": "final",
                    "code": {"text": "Hemoglobin"},
                    "valueQuantity": {
                        "value": 13.5,
                        "unit": "g/dL",
                    },
                }
            }
        ],
    }

    result = extract_clinical_context([bundle])

    assert result["observations"][0]["value"]["value"] == 13.5
    assert result["observations"][0]["value"]["unit"] == "g/dL"
