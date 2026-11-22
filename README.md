# EHR Media Intelligence Platform

An MVP that ingests heterogeneous EHR media records, normalizes them, maps them to HL7 FHIR R4, generates AI-assisted clinical summaries, and provides semantic search for clinicians.

## Current implementation status

- [x] Project scaffold and FastAPI health endpoint
- [x] Task 1: JSON, CSV, and key-value plain-text ingestion
- [x] Canonical Pydantic v2 intermediate models
- [x] Date, gender, and MRN normalization
- [x] Duplicate detection and identity-conflict flags
- [x] Per-record and batch audit events
- [x] Unit tests for cleaning edge cases
- [ ] Task 2: FHIR R4 mapping and Bundle validation
- [ ] Task 3: AI clinical summarization and cache
- [ ] Task 4: Semantic search
- [ ] Task 5: Clinician search UI

## Requirements

- Python 3.11+
- Git

## Backend setup

From the repository root:

```bash
cd backend
python -m venv .venv
```

Activate the environment:

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run tests:

```bash
pytest -q
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Open API documentation at http://127.0.0.1:8000/docs.

## Try ingestion

Use the interactive Swagger UI at `/docs`, select `POST /ingestion/upload`, and upload one of:

- `backend/data/input/sample_records.json`
- `backend/data/input/sample_records.csv`
- `backend/data/input/sample_note.txt`

Or use curl:

```bash
curl -X POST "http://127.0.0.1:8000/ingestion/upload" \
  -F "file=@data/input/sample_records.json"
```

## Frontend preview

From the repository root, run:

```bash
python -m http.server 5500 --directory frontend
```

Open http://127.0.0.1:5500.

## Data safety

Use synthetic data only in this development project. Do not upload real patient information to an unapproved environment or LLM provider. Before real clinical deployment, implement authentication, authorization, audit retention, encryption, secure hosting, clinical validation, and applicable regulatory review.

## Design decisions

- Modular monolith: simple to run and test while keeping domain boundaries clear.
- Pydantic intermediate representation: validates and standardizes data before FHIR mapping.
- Identity conflicts are flagged, not auto-merged.
- MRN normalization preserves leading zeroes.
- Exact duplicate records are skipped and recorded in a batch audit log.
- Synthetic samples allow repeatable tests without exposing patient data.

## Security and deployment status

This repository is a synthetic-data MVP and is not approved for real patient data or clinical use. Read [SECURITY.md](SECURITY.md) before running or deploying it. The ingestion endpoint currently has no authentication or patient-level authorization; run it only in a trusted local development environment. Configure `CORS_ORIGINS` with exact frontend origins. Never commit `.env`, patient data, local databases, uploaded files, or vector-store data.

The upload pipeline enforces a 10 MiB file limit, record and field limits, UTF-8 decoding, supported extensions, and format-specific parsing. Audit events intentionally omit old/new field values because they can contain sensitive patient information. API validation errors are sanitized and do not echo rejected input.

### Local configuration

Copy `backend/.env.example` to `backend/.env` only if you need local overrides. Keep the populated `.env` file out of version control.


## Task 2 — FHIR R4 normalization

The FHIR API accepts the JSON `IngestionReport` returned by `POST /ingestion/upload`.

1. Send that response body to `POST /fhir/normalize`.
2. The service creates one FHIR R4 `Bundle` of type `collection` per patient.
3. Bundles contain `Patient`, `Encounter`, and either `DiagnosticReport` or `DocumentReference` resources.
4. Each clinical resource references its `Patient` and associated `Encounter`. All local references are checked against resources in the same Bundle.
5. Validated Bundles are stored in `backend/storage/fhir_bundles.sqlite3` (ignored by Git).
6. Retrieve stored Bundles with `GET /fhir/bundles/{patient_id}`. Here `patient_id` is the generated FHIR Patient resource ID returned in the Bundle, not the source MRN.

### FHIR implementation notes

- `fhir.resources==7.1.0` is pinned because its generated models target FHIR R4 and use Pydantic v2.
- `fhir.resources` model validation checks resource structure. This MVP also checks local references; it does not replace the official HL7 FHIR validator, terminology validation, or profile validation.
- Lab/result records map to `DiagnosticReport`. Notes, imaging documents, discharge summaries, and unrecognized source record types are retained as `DocumentReference` resources.
- Source clinical text is base64-encoded in `DocumentReference.content.attachment.data`, as required by FHIR Attachment.
- Identity conflicts flagged by Task 1 are deliberately kept in separate patient Bundles instead of being silently merged.
- `Encounter` resources are created as synthetic encounter context because the input dataset does not contain a dedicated encounter entity. This is a demo mapping assumption, not a claim that a real clinical encounter was verified.
- The platform remains synthetic-data-only and is not approved for real patient data or clinical use.

### Try Task 2

Start the API, upload one of the sample files using `POST /ingestion/upload`, then copy the complete JSON response into the request body for `POST /fhir/normalize`. The response includes the patient Bundles and their generated Patient IDs. Use one of those IDs with `GET /fhir/bundles/{patient_id}`.
