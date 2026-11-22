from types import SimpleNamespace

from app.schemas.search import SearchRequest
from app.search import service
from datetime import date


class FakeModel:
    def encode(self, texts, **kwargs):
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeCollection:
    def __init__(self):
        self.items = {}
        self.last_query = None

    def get(self, include=None):
        return {"ids": list(self.items), "metadatas": []}

    def upsert(self, ids, documents, metadatas, embeddings):
        for item_id, document, metadata in zip(ids, documents, metadatas):
            self.items[item_id] = (document, metadata)

    def delete(self, ids):
        for item_id in ids:
            self.items.pop(item_id, None)

    def count(self):
        return len(self.items)

    def query(self, **kwargs):
        self.last_query = kwargs
        if not self.items:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        item_id, (document, metadata) = next(iter(self.items.items()))
        return {
            "ids": [[item_id]],
            "documents": [[document]],
            "metadatas": [[metadata]],
            "distances": [[0.2]],
        }


def test_search_builds_index_and_returns_ranked_results(monkeypatch):
    collection = FakeCollection()
    bundle = {
        "id": "b-1",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "p-1",
                          "name": [{"text": "Jane Doe"}]}},
            {"resource": {"resourceType": "DiagnosticReport", "id": "r-1",
                          "code": {"text": "CBC"}, "conclusion": "Hemoglobin 11.2 g/dL",
                          "effectiveDateTime": "2026-11-20"}},
        ],
    }

    monkeypatch.setattr(service, "get_all_bundles", lambda: [bundle])
    monkeypatch.setattr(service, "get_collection", lambda: collection)
    monkeypatch.setattr(service, "_encode", lambda texts: [[0.1, 0.2, 0.3] for _ in texts])

    indexed = service.index_fhir_records()

    assert indexed["documents_indexed"] == 1
    assert collection.count() == 1

    response = service.search_clinical_records(
        SearchRequest(query="low hemoglobin", top_k=5)
    )

    assert response.total_results == 1
    assert response.results[0].patient_name == "Jane Doe"
    assert response.results[0].resource_type == "DiagnosticReport"
    assert response.results[0].relevance_score == 0.9


def test_search_applies_resource_and_date_filters(monkeypatch):
    collection = FakeCollection()
    collection.items["existing"] = (
        "CBC Hemoglobin 11.2 g/dL",
        {
            "patient_id": "p-1",
            "patient_name": "Jane Doe",
            "mrn": "",
            "resource_type": "DiagnosticReport",
            "resource_id": "r-1",
            "record_date": "2026-11-20",
            "title": "CBC",
        },
    )
    monkeypatch.setattr(service, "get_collection", lambda: collection)
    monkeypatch.setattr(service, "_encode", lambda texts: [[0.1, 0.2, 0.3]])

    service.search_clinical_records(
        SearchRequest(
            query="hemoglobin",
            resource_type="DiagnosticReport",
            date_from="2026-11-01",
            date_to="2026-11-30",
        )
    )

    assert collection.last_query["where"]["$and"] == [
    {"resource_type": "DiagnosticReport"},
    {"record_date_sort": {"$gt": 0}},
    {
        "record_date_sort": {
            "$gte": date(2026, 11, 1).toordinal()
        }
    },
    {
        "record_date_sort": {
            "$lte": date(2026, 11, 30).toordinal()
        }
    },
]


def test_search_rejects_empty_index(monkeypatch):
    collection = FakeCollection()
    monkeypatch.setattr(service, "get_collection", lambda: collection)

    try:
        service.search_clinical_records(SearchRequest(query="chest pain"))
        assert False, "Expected SearchIndexEmptyError"
    except service.SearchIndexEmptyError:
        pass




