"""Lazy ChromaDB access; importing the API does not download the embedding model."""
from __future__ import annotations

from functools import lru_cache

from app.config import VECTOR_STORE_DIR

COLLECTION_NAME = "ehr_clinical_records"


@lru_cache(maxsize=1)
def get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Semantic-search dependencies are missing. Install backend/requirements.txt."
        ) from exc

    from app.config import EMBEDDING_DEVICE, EMBEDDING_MODEL

    return SentenceTransformer(EMBEDDING_MODEL, device=EMBEDDING_DEVICE)


@lru_cache(maxsize=1)
def get_collection():
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            "ChromaDB is not installed. Install backend/requirements.txt."
        ) from exc

    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
