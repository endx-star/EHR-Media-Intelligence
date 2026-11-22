"""Semantic search and vector-index management endpoints."""
from fastapi import APIRouter, HTTPException, status

from app.schemas.search import SearchRequest, SearchResponse
from app.search.service import (
    SearchIndexEmptyError,
    index_fhir_records,
    search_clinical_records,
)

router = APIRouter(prefix="/search", tags=["Semantic Search"])


@router.post(
    "",
    response_model=SearchResponse,
    summary="Search clinical records semantically",
)
def search_records(request: SearchRequest) -> SearchResponse:
    try:
        return search_clinical_records(request)
    except SearchIndexEmptyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post(
    "/index",
    summary="Build or refresh the semantic search index",
)
def rebuild_search_index() -> dict[str, int]:
    try:
        return index_fhir_records()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
