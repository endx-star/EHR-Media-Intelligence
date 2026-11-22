# Security Policy

## Project status

EHR Media Intelligence Platform is an educational/demo MVP. The included data must be synthetic. The application is not approved for processing real patient information or for clinical use.

## Development requirements

- Never commit API keys, passwords, access tokens, private keys, or populated `.env` files.
- Never commit real patient records, protected health information (PHI), uploaded documents, generated clinical data, local databases, or vector indexes.
- Use synthetic data for development and tests.
- Keep secrets in environment variables or an approved secrets manager.
- Validate file format and content, enforce upload/record/field limits, and do not trust client-provided MIME types.
- Do not include patient values or clinical text in general application logs or audit metadata.
- Keep CORS restricted to explicitly configured frontend origins.

## Clinical safety

AI-generated summaries are informational outputs, not diagnoses or clinical decisions. A qualified clinician must independently review clinical information before any real-world use.

## Reporting vulnerabilities

Do not publish credentials, patient information, or exploitable vulnerabilities in public issues. Contact the repository maintainer privately.

## Before real deployment

A production deployment requires, at minimum, authentication, authorization and patient-level access controls, encryption in transit and at rest, secure secrets management, protected audit logging, backup/recovery procedures, dependency and penetration testing, clinical validation, and review of applicable privacy and healthcare regulations. This repository does not currently provide those controls and must not be exposed to real patient data.
