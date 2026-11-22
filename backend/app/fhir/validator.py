
"""FHIR R4 4.0.1 validation and internal reference integrity checks."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.config import BASE_DIR


FHIR_VERSION = "4.0.1"
VALIDATOR_TIMEOUT_SECONDS = 120


class FHIRValidationError(ValueError):
    """Raised when a FHIR Bundle fails validation."""


def _get_validator_jar() -> Path:
    """Resolve the configured HL7 validator JAR path."""

    configured_path = os.getenv("FHIR_VALIDATOR_JAR")

    if not configured_path:
        raise FHIRValidationError(
            "FHIR Validator is not configured. "
            "Set FHIR_VALIDATOR_JAR in your backend .env file."
        )

    jar_path = Path(configured_path).expanduser()

    if not jar_path.is_absolute():
        jar_path = BASE_DIR / jar_path

    if not jar_path.is_file():
        raise FHIRValidationError(
            "The configured FHIR Validator JAR file could not be found."
        )

    return jar_path


def _run_hl7_validator(bundle_data: dict[str, Any]) -> None:
    """Validate a Bundle using the official HL7 FHIR R4 validator."""

    jar_path = _get_validator_jar()
    java_command = os.getenv("JAVA_COMMAND", "java")

    with tempfile.TemporaryDirectory(prefix="fhir-r4-") as temp_dir:
        bundle_path = Path(temp_dir) / "bundle.json"

        bundle_path.write_text(
            json.dumps(bundle_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        command = [
            java_command,
            "-jar",
            str(jar_path),
            str(bundle_path),
            "-version",
            FHIR_VERSION,
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=VALIDATOR_TIMEOUT_SECONDS,
                check=False,
            )

        except FileNotFoundError as exc:
            raise FHIRValidationError(
                "Java was not found. Install Java and ensure it is available "
                "through your PATH environment variable."
            ) from exc

        except subprocess.TimeoutExpired as exc:
            raise FHIRValidationError(
                "FHIR R4 validation timed out."
            ) from exc

        output = "\n".join(
            part.strip()
            for part in (result.stdout, result.stderr)
            if part and part.strip()
        )

        if result.returncode != 0:
            details = output[-3000:] if output else "No validator output."

            raise FHIRValidationError(
                "FHIR R4 4.0.1 validation failed:\n" + details
            )


def _validate_internal_references(
    bundle_data: dict[str, Any],
) -> None:
    """Ensure references to resources inside the Bundle resolve."""

    entries = bundle_data.get("entry", [])

    available_references: set[str] = set()

    for entry in entries:
        resource = entry.get("resource", {})

        resource_type = resource.get("resourceType")
        resource_id = resource.get("id")

        if resource_type and resource_id:
            available_references.add(
                f"{resource_type}/{resource_id}"
            )

        full_url = entry.get("fullUrl")

        if isinstance(full_url, str):
            available_references.add(full_url)

    references: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            reference = value.get("reference")

            if (
                isinstance(reference, str)
                and "/" in reference
                and not reference.startswith(
                    ("http://", "https://", "urn:", "#")
                )
            ):
                references.append(reference)

            for child in value.values():
                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(bundle_data)

    unresolved = sorted(
        {
            reference
            for reference in references
            if reference not in available_references
        }
    )

    if unresolved:
        raise FHIRValidationError(
            "FHIR Bundle contains unresolved references: "
            + ", ".join(unresolved)
        )


def validate_bundle(
    bundle_data: dict[str, Any],
) -> dict[str, Any]:
    """Validate Bundle structure against FHIR R4 4.0.1."""

    if not isinstance(bundle_data, dict):
        raise FHIRValidationError(
            "FHIR Bundle must be a JSON object."
        )

    if bundle_data.get("resourceType") != "Bundle":
        raise FHIRValidationError(
            "The supplied resource must have resourceType 'Bundle'."
        )

    if not isinstance(bundle_data.get("entry", []), list):
        raise FHIRValidationError(
            "FHIR Bundle entry must be a list."
        )

    # Check references before invoking the external validator.
    _validate_internal_references(bundle_data)

    # Validate against the official FHIR R4 4.0.1 specification.
    _run_hl7_validator(bundle_data)

    return bundle_data
