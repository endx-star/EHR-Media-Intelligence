from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import search as search_api
from app.schemas.search import SearchResponse


def test_search_endpoint_returns_results(monkeypatch):
    expected = SearchResponse(
        query="hemoglobin",
        results=[],
        total_results=0,
        search_time_ms=2.5,
    )
    monkeypatch.setattr(
        search_api,
        "search_clinical_records",
        lambda request: expected,
    )

    app = FastAPI()
    app.include_router(search_api.router)
    response = TestClient(app).post(
        "/search",
        json={"query": "hemoglobin"},
    )

    assert response.status_code == 200
    assert response.json()["query"] == "hemoglobin"
    assert response.json()["total_results"] == 0


def test_search_endpoint_reports_empty_index(monkeypatch):
    def raise_empty(request):
        raise search_api.SearchIndexEmptyError("Index is empty.")

    monkeypatch.setattr(search_api, "search_clinical_records", raise_empty)

    app = FastAPI()
    app.include_router(search_api.router)
    response = TestClient(app).post(
        "/search",
        json={"query": "hemoglobin"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Index is empty."
