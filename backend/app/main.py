from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ingestion import router as ingestion_router
from app.config import CORS_ORIGINS

app = FastAPI(
    title="EHR Media Intelligence Platform",
    description=(
        "Synthetic-data MVP for EHR media ingestion, normalization, "
        "summarization, and search. Not approved for clinical use."
    ),
    version="0.1.1",
)

# Explicit local origins by default. Set CORS_ORIGINS to a comma-separated
# allowlist when deploying the frontend. Never use wildcard origins with
# credentialed requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(ingestion_router)


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "ehr-media-intelligence"}
