import pytest
from pydantic import ValidationError

from app.schemas.search import SearchRequest


def test_search_request_defaults_to_five_results():
    request = SearchRequest(query="chest pain")

    assert request.top_k == 5
    assert request.resource_type is None


def test_search_request_rejects_invalid_date_range():
    with pytest.raises(ValidationError):
        SearchRequest(
            query="laboratory results",
            date_from="2026-11-22",
            date_to="2026-11-20",
        )


def test_search_request_rejects_unsupported_resource_type():
    with pytest.raises(ValidationError):
        SearchRequest(
            query="patient notes",
            resource_type="Patient",
        )


def test_search_request_rejects_extra_fields():
    with pytest.raises(ValidationError):
        SearchRequest(query="chest xray", unexpected="value")
