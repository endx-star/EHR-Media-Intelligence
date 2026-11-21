# Security Policy

## Project Scope

EHR Media Intelligence Platform is currently an educational and demonstration MVP. It uses synthetic patient data and is not approved for processing real patient information or clinical deployment.

## Supported Development Practices

- Never commit API keys, passwords, tokens, or other credentials.
- Never commit real patient records or protected health information (PHI).
- Use synthetic data for development and testing.
- Store local secrets in environment variables.
- Exclude generated databases, uploaded documents, and vector-store files from version control.
- Validate uploaded files and enforce file-size restrictions.
- Avoid exposing sensitive patient information in application logs and error messages.

## Clinical Safety

AI-generated summaries are informational outputs and must not be treated as medical diagnoses or clinical decisions.

## Reporting Security Issues

Please do not disclose credentials, patient information, or exploitable vulnerabilities in public issues.

Report security concerns privately to the repository maintainer.

## Production Readiness

Before deployment in a real healthcare environment, the application requires security testing, authentication, authorization, encryption, audit controls, clinical validation, and assessment against applicable healthcare regulations.