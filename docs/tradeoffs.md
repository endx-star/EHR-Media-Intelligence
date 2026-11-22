# Technical tradeoffs and validation notes

This is a development MVP built around synthetic EHR records. JSON, CSV, and a documented key-value text format were selected to demonstrate heterogeneous ingestion without requiring access to a live Epic environment. Pydantic models provide a canonical intermediate representation before FHIR mapping. SQLite and a local vector store are planned to keep the MVP easy to run; a production deployment would likely use managed PostgreSQL and durable object storage.

Patient identity collisions are flagged rather than automatically merged because incorrect patient matching can create serious clinical safety risks. MRN normalization removes display separators but preserves leading zeroes. Exact duplicate records are skipped based on a deterministic content hash and recorded in the batch audit log.

With more time, the system should add robust OCR for scanned PDFs, terminology mapping using LOINC/SNOMED CT/RxNorm, formal FHIR R4 profile validation, SMART on FHIR authentication, role-based and patient-context authorization, immutable audit storage, a durable background queue, and clinician review workflows. AI summary quality should be evaluated against clinician-authored reference summaries using a structured rubric for factual consistency, omission, unsupported claims, source traceability, and readability. No AI-generated summary should be treated as a clinical decision.


## Task 2 — FHIR R4 mapping trade-offs

- **FHIR version:** Pin `fhir.resources` 7.1.0 for R4 rather than allowing an unbounded upgrade that may change the default FHIR release.
- **Bundle type:** Use `collection` because the platform is packaging related resources for storage and downstream analysis, not asking a FHIR server to execute a transaction.
- **Encounter generation:** Input files do not provide encounter identifiers. A synthetic Encounter is generated per source record to provide a resolvable context reference. A production mapping should use source encounter IDs and must not invent clinical encounters.
- **Identity collisions:** Task 1 collision flags prevent automatic merging. The FHIR layer assigns separate generated patient IDs to conflicting identities pending manual reconciliation.
- **Validation scope:** Pydantic FHIR model validation plus local-reference checks provide useful structural safeguards. Full conformance requires the official HL7 validator, profiles, terminology services, and implementation-guide-specific rules.
