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
- [x] Task 2: FHIR R4 mapping and Bundle validation
- [x] Task 3: AI clinical summarization and cache
- [x] Task 4: Semantic search API and persistent vector index
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


## Task 4 — Semantic search

The semantic-search layer indexes clinical text from the stored FHIR R4 Bundles. SQLite remains the source of truth; ChromaDB is a derived vector index that can be rebuilt at any time.

### Search architecture

- **Document extraction:** `backend/app/search/document_builder.py` extracts text and metadata from `DiagnosticReport`, `DocumentReference`, and `Observation` resources.
- **Embeddings:** Sentence Transformers uses `sentence-transformers/all-MiniLM-L6-v2` to convert clinical text and user queries into vectors.
- **Vector storage:** ChromaDB persists embeddings under `backend/storage/chroma/`.
- **Retrieval:** cosine-distance ranking returns the top matching records with a normalized relevance score between 0 and 1.
- **Filters:** search supports patient ID, resource type, and inclusive date range filters.
- **Rebuilding:** the index is rebuilt from SQLite, updates existing documents, and removes stale vector entries.

The initial embedding model is downloaded the first time indexing or search runs. The first request may therefore be slower; subsequent searches use the local model cache. The model runs on CPU by default. For the assignment's 50-record performance check, warm the model before measuring search latency.

### Install Task 4 dependencies

From `backend` with the virtual environment activated:

```powershell
python -m pip install -r requirements.txt
```

### Build or refresh the vector index

1. Upload a synthetic JSON, CSV, or text file using `POST /ingestion/upload`.
2. Send the resulting ingestion report to `POST /fhir/normalize`.
3. Call `POST /search/index` once to build the vector index from all FHIR Bundles stored in SQLite.

Example response:

```json
{
  "bundles_read": 2,
  "documents_indexed": 4,
  "documents_skipped": 0,
  "stale_documents_removed": 0
}
```

Run `POST /search/index` again after adding or changing FHIR Bundles. Reindexing is safe to repeat.

### Search endpoint

`POST /search`

Example request:

```json
{
  "query": "Find records mentioning low hemoglobin",
  "top_k": 5,
  "resource_type": "DiagnosticReport",
  "date_from": "2026-11-01",
  "date_to": "2026-11-30"
}
```

All filters except `query` are optional. Supported resource types are `DiagnosticReport`, `DocumentReference`, and `Observation`. `top_k` defaults to 5 and is limited to 20.

Each result includes the patient ID, patient name, MRN when available, FHIR resource type and ID, record date, title, text snippet, and relevance score. The score is a normalized cosine-similarity indicator, not a clinical confidence score.

If the index has not been built, the endpoint returns HTTP 409 and instructs the caller to run `POST /search/index`.

### Search limitations

- Only text-based `DocumentReference` attachments are indexed. PDF/image OCR is not implemented.
- The current FHIR mapper represents source lab records as `DiagnosticReport`; the search index also supports `Observation` if those resources are added later.
- Embeddings support semantic retrieval, but relevance must be evaluated against representative synthetic queries. A high similarity score does not establish clinical correctness.
- This MVP is for synthetic data only. Do not index real patient information or deploy without authentication, patient-level authorization, audit controls, and an approved privacy/security review.
