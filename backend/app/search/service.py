"""Index FHIR clinical documents and perform semantic similarity search."""
from __future__ import annotations

from time import perf_counter
from typing import Any

from app.fhir.storage import get_all_bundles
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.search.document_builder import build_search_documents
from app.search.vector_store import get_collection, get_embedding_model


class SearchIndexEmptyError(Exception):
    """Raised when a search is attempted before records are indexed."""


def _encode(texts: list[str]):
    model = get_embedding_model()
    return model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )


def _as_list(vector):
    return vector.tolist() if hasattr(vector, "tolist") else list(vector)


def index_fhir_records() -> dict[str, int]:
    """Rebuild the vector index from the authoritative FHIR SQLite store."""
    bundles = get_all_bundles()
    documents = build_search_documents(bundles)
    collection = get_collection()

    existing = collection.get(include=["metadatas"])
    existing_ids = set(existing.get("ids") or [])
    current_ids = {item["id"] for item in documents}

    # Remove stale entries so replaced/deleted FHIR records do not remain searchable.
    stale_ids = existing_ids - current_ids
    if stale_ids:
        collection.delete(ids=list(stale_ids))

    if not documents:
        return {
            "bundles_read": len(bundles),
            "documents_indexed": 0,
            "documents_skipped": 0,
            "stale_documents_removed": len(stale_ids),
        }

    # Batch embedding to limit memory use on developer machines.
    batch_size = 64
    for start in range(0, len(documents), batch_size):
        batch = documents[start:start + batch_size]
        embeddings = _encode([item["document"] for item in batch])
        collection.upsert(
            ids=[item["id"] for item in batch],
            documents=[item["document"] for item in batch],
            metadatas=[item["metadata"] for item in batch],
            embeddings=[_as_list(vector) for vector in embeddings],
        )

    return {
        "bundles_read": len(bundles),
        "documents_indexed": len(documents),
        "documents_skipped": sum(
            1 for bundle in bundles for entry in bundle.get("entry", [])
            if entry.get("resource", {}).get("resourceType")
            in {"DiagnosticReport", "DocumentReference", "Observation"}
        ) - len(documents),
        "stale_documents_removed": len(stale_ids),
    }


def _build_where(request: SearchRequest) -> dict[str, Any] | None:
    conditions = []

    if request.resource_type:
        conditions.append({"resource_type": request.resource_type})

    if request.patient_id:
        conditions.append({"patient_id": request.patient_id})

    if request.date_from or request.date_to:
        # Exclude records without a valid date.
        conditions.append({"record_date_sort": {"$gt": 0}})

    if request.date_from:
        conditions.append({
            "record_date_sort": {
                "$gte": request.date_from.toordinal()
            }
        })

    if request.date_to:
        conditions.append({
            "record_date_sort": {
                "$lte": request.date_to.toordinal()
            }
        })

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return {"$and": conditions}


def search_clinical_records(request: SearchRequest) -> SearchResponse:
    started = perf_counter()
    collection = get_collection()

    if collection.count() == 0:
        raise SearchIndexEmptyError(
            "The semantic search index is empty. Run POST /search/index first."
        )

    query_embedding = _encode([request.query])[0]
    query_args: dict[str, Any] = {
        "query_embeddings": [_as_list(query_embedding)],
        "n_results": min(request.top_k, collection.count()),
        "include": ["documents", "metadatas", "distances"],
    }
    where = _build_where(request)
    if where:
        query_args["where"] = where

    matches = collection.query(**query_args)
    ids = (matches.get("ids") or [[]])[0]
    docs = (matches.get("documents") or [[]])[0]
    metadatas = (matches.get("metadatas") or [[]])[0]
    distances = (matches.get("distances") or [[]])[0]

    results = []
    for doc_id, document, metadata, distance in zip(
        ids, docs, metadatas, distances
    ):
        # Chroma cosine distance is in [0, 2]; map it to a readable [0, 1] score.
        score = max(0.0, min(1.0, 1.0 - float(distance) / 2.0))
        results.append(SearchResult(
            patient_id=str(metadata.get("patient_id", "")),
            patient_name=metadata.get("patient_name") or None,
            mrn=metadata.get("mrn") or None,
            resource_type=str(metadata.get("resource_type", "")),
            resource_id=str(metadata.get("resource_id", "")),
            record_date=metadata.get("record_date") or None,
            title=str(metadata.get("title") or "Clinical record"),
            snippet=str(document or "")[:600],
            relevance_score=round(score, 4),
        ))

    return SearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
        search_time_ms=round((perf_counter() - started) * 1000, 2),
    )
