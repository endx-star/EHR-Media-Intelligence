
import json
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000"
JSON_FILE = Path("EHR_50_Records.json")


def main():
    if not JSON_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {JSON_FILE.resolve()}"
        )

    with httpx.Client(timeout=180.0) as client:

        # Step 1: Upload and clean synthetic EHR records
        print("\n[1/3] Uploading synthetic EHR records...")

        with JSON_FILE.open("rb") as file:
            response = client.post(
                f"{BASE_URL}/ingestion/upload",
                files={
                    "file": (
                        JSON_FILE.name,
                        file,
                        "application/json",
                    )
                },
            )

        response.raise_for_status()
        report = response.json()

        print("Ingestion results:")
        print(f"Total:     {report['total_input_records']}")
        print(f"Accepted:  {report['accepted_records']}")
        print(f"Rejected:  {report['rejected_records']}")
        print(f"Duplicates:{report['duplicate_records']}")

        if report["accepted_records"] != 50:
            raise RuntimeError(
                "Expected 50 accepted records. "
                "Check the ingestion response before continuing."
            )

        # Step 2: Normalize and store FHIR R4 Bundles
        print("\n[2/3] Normalizing records into FHIR R4...")

        response = client.post(
            f"{BASE_URL}/fhir/normalize",
            json=report,
        )

        response.raise_for_status()
        fhir_result = response.json()

        print("FHIR normalization results:")
        print(
            "Patients processed:",
            fhir_result["patients_processed"],
        )

        # Step 3: Build the semantic search index
        print("\n[3/3] Building ChromaDB search index...")

        response = client.post(
            f"{BASE_URL}/search/index"
        )

        response.raise_for_status()

        print("Search indexing response:")
        if response.content:
            try:
                print(json.dumps(response.json(), indent=2))
            except ValueError:
                print(response.text)
        else:
            print("Indexing completed successfully.")

        print("\nAll three workflow steps completed.")


if __name__ == "__main__":
    main()
