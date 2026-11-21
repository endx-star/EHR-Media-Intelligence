from app.ingestion.cleaner import build_report, clean_one, normalize_mrn
from app.ingestion.parsers import parse_csv_text, parse_json_text, parse_plain_text


def test_mrn_normalization_preserves_leading_zeroes():
    record = clean_one({"mrn": "  ab-001  ", "patient_name": "Jane Doe"}, "json")
    assert record.patient.mrn == "AB001"
    assert any(item.field == "patient.mrn" for item in record.audit_log)


def test_inconsistent_dates_and_gender_are_normalized():
    record = clean_one(
        {"mrn": "0012", "dob": "03/04/1980", "date": "Nov 20, 2026", "sex": "F"},
        "csv",
    )
    assert record.patient.date_of_birth.isoformat() == "1980-03-04"
    assert record.record_date.isoformat() == "2026-11-20"
    assert record.patient.gender.value == "female"


def test_missing_gender_defaults_to_unknown_and_is_audited():
    record = clean_one({"mrn": "0012", "content": "CBC report"}, "json")
    assert record.patient.gender.value == "unknown"
    assert any(item.action == "defaulted" for item in record.audit_log)


def test_exact_duplicate_records_are_skipped():
    raw = [
        {"mrn": "001", "date": "2026-01-01", "title": "CBC", "content": "Hb 12"},
        {"mrn": "001", "date": "2026-01-01", "title": "CBC", "content": "Hb 12"},
    ]
    report = build_report(raw, "json")
    assert report.accepted_records == 1
    assert report.duplicate_records == 1
    assert report.batch_audit[0].action == "duplicate_skipped"


def test_conflicting_patient_identifiers_are_flagged_not_merged():
    raw = [
        {"mrn": "001", "patient_id": "EHR-A", "patient_name": "Jane Doe", "content": "note one"},
        {"mrn": "001", "patient_id": "EHR-B", "patient_name": "Jane Doe", "content": "note two"},
    ]
    report = build_report(raw, "json")
    assert report.accepted_records == 2
    assert report.identity_conflicts >= 1
    assert all(record.identity_conflict for record in report.records)


def test_json_csv_and_text_parsers():
    assert len(parse_json_text('[{"mrn":"1"}]')) == 1
    assert parse_csv_text("mrn,content\n1,hello")[0]["mrn"] == "1"
    text_record = parse_plain_text("MRN: 001\nPatient Name: Jane Doe\nContent: CBC normal")
    assert text_record[0]["mrn"] == "001"
    assert text_record[0]["content"] == "CBC normal"


def test_same_source_patient_id_with_multiple_mrns_is_flagged():
    raw = [
        {"mrn": "001", "patient_id": "EHR-X", "content": "first note"},
        {"mrn": "002", "patient_id": "EHR-X", "content": "second note"},
    ]
    report = build_report(raw, "json")
    assert report.identity_conflicts == 2
    assert all(record.identity_conflict for record in report.records)
