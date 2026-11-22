import base64

from app.search.document_builder import build_search_documents


def test_build_search_documents_extracts_fhir_diagnostic_report():
    bundle = {
        "resourceType": "Bundle",
        "id": "bundle-1",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-1",
                    "name": [{"text": "Jane Doe"}],
                    "identifier": [
                        {"system": "https://example.test/identifier/mrn", "value": "000123"}
                    ],
                }
            },
            {
                "resource": {
                    "resourceType": "DiagnosticReport",
                    "id": "report-1",
                    "status": "final",
                    "code": {"text": "Complete Blood Count"},
                    "effectiveDateTime": "2026-11-20",
                    "conclusion": "Hemoglobin 11.2 g/dL.",
                }
            },
        ],
    }

    docs = build_search_documents([bundle])

    assert len(docs) == 1
    assert "Complete Blood Count" in docs[0]["document"]
    assert "Hemoglobin 11.2 g/dL." in docs[0]["document"]
    assert docs[0]["metadata"]["patient_id"] == "patient-1"
    assert docs[0]["metadata"]["patient_name"] == "Jane Doe"
    assert docs[0]["metadata"]["mrn"] == "000123"
    assert docs[0]["metadata"]["record_date"] == "2026-11-20"
    assert docs[0]["metadata"]["resource_type"] == "DiagnosticReport"


def test_build_search_documents_decodes_text_document_reference():
    text = "Patient discharged home. Follow up with primary care."
    encoded = base64.b64encode(text.encode()).decode()
    bundle = {
        "id": "bundle-2",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "p-2"}},
            {
                "resource": {
                    "resourceType": "DocumentReference",
                    "id": "doc-2",
                    "type": {"text": "Discharge summary"},
                    "date": "2026-11-21T00:00:00Z",
                    "content": [{
                        "attachment": {
                            "contentType": "text/plain",
                            "title": "Discharge summary",
                            "data": encoded,
                        }
                    }],
                }
            },
        ],
    }

    docs = build_search_documents([bundle])

    assert len(docs) == 1
    assert text in docs[0]["document"]
    assert docs[0]["metadata"]["resource_type"] == "DocumentReference"
    assert docs[0]["metadata"]["record_date"] == "2026-11-21"


def test_non_text_attachment_is_not_decoded():
    encoded = base64.b64encode(b"binary-content").decode()
    bundle = {
        "id": "bundle-3",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "p-3"}},
            {
                "resource": {
                    "resourceType": "DocumentReference",
                    "id": "doc-3",
                    "type": {"text": "Scanned document"},
                    "content": [{
                        "attachment": {
                            "contentType": "application/pdf",
                            "data": encoded,
                        }
                    }],
                }
            },
        ],
    }

    docs = build_search_documents([bundle])

    # The title remains searchable; binary PDF content is deliberately not decoded.
    assert len(docs) == 1
    assert docs[0]["document"] == "Scanned document"


def test_resources_without_patient_or_searchable_text_are_skipped():
    bundle = {
        "id": "bundle-4",
        "entry": [
            {"resource": {"resourceType": "DiagnosticReport", "id": "r-1"}},
        ],
    }

    assert build_search_documents([bundle]) == []
