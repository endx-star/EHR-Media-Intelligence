from fastapi.testclient import TestClient

from app.main import app
from app.ingestion.parsers import InputParseError, parse_csv_text, parse_json_text, parse_file

client = TestClient(app)


def test_json_parser_rejects_malformed_json_without_echoing_content():
    secret_like_patient_text = '{"name":"PRIVATE_PATIENT",'
    try:
        parse_json_text(secret_like_patient_text)
        assert False, "Expected malformed JSON to be rejected"
    except InputParseError as exc:
        assert "PRIVATE_PATIENT" not in str(exc)


def test_csv_parser_rejects_duplicate_headers():
    try:
        parse_csv_text("mrn,MRN\n001,002")
        assert False, "Expected duplicate headers to be rejected"
    except InputParseError as exc:
        assert "duplicate" in str(exc).lower()


def test_parser_rejects_unsupported_extension():
    try:
        parse_file("payload.exe", b"not a supported format")
        assert False, "Expected unsupported file type to be rejected"
    except InputParseError as exc:
        assert "unsupported" in str(exc).lower()


def test_upload_rejects_invalid_json_with_sanitized_error():
    response = client.post(
        "/ingestion/upload",
        files={"file": ("bad.json", b'{"patient_name":"PRIVATE_PATIENT",', "application/json")},
    )
    assert response.status_code == 400
    assert "PRIVATE_PATIENT" not in response.text


def test_audit_events_do_not_store_old_or_new_values():
    response = client.post(
        "/ingestion/upload",
        files={
            "file": (
                "record.json",
                b'[{"mrn":" private-001 ","patient_name":"Synthetic Person","dob":"1980-01-02"}]',
                "application/json",
            )
        },
    )
    assert response.status_code == 200
    payload = response.json()
    audit = payload["records"][0]["audit_log"]
    assert audit
    assert all("old_value" not in event and "new_value" not in event for event in audit)
    assert "private-001" not in response.text
