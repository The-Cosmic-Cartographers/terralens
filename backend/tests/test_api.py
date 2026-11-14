"""API v1 part A against the SAMPLE fixtures, and against an empty data folder."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import CatalogueItem, ErrorResponse, Health, Metadata, Region

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"
SAMPLE = "SAMPLE — NOT NASA DATA"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TERRALENS_DATA_DIR", str(FIXTURES))
    return TestClient(app)


@pytest.fixture
def empty_client(monkeypatch, tmp_path):
    monkeypatch.setenv("TERRALENS_DATA_DIR", str(tmp_path))
    return TestClient(app)


def assert_error(response, status, code):
    assert response.status_code == status
    error = ErrorResponse(**response.json()).error
    assert error.code == code
    return error


def test_health_reports_the_data_version(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert Health(**response.json()).data_version == SAMPLE


def test_health_works_without_any_data(empty_client):
    body = empty_client.get("/health").json()
    assert body == {"status": "ok", "data_version": "unversioned"}


def test_catalogue_lists_ready_and_coming_soon_datasets(client):
    response = client.get("/api/v1/catalogue")
    assert response.status_code == 200
    items = [CatalogueItem(**i) for i in response.json()]
    assert {i.status for i in items} == {"ready", "coming_soon"}
    assert "sample_t2m" in {i.dataset_id for i in items}


def test_regions_carry_geometry_and_source(client):
    response = client.get("/api/v1/regions")
    assert response.status_code == 200
    regions = [Region(**r) for r in response.json()]
    assert [r.region_id for r in regions] == ["ireland", "iberia"]
    assert all(r.geometry and r.geometry["type"] == "Polygon" for r in regions)


def test_metadata_returns_provenance_and_marks_sample(client):
    response = client.get("/api/v1/metadata", params={"dataset_id": "sample_t2m"})
    assert response.status_code == 200
    metadata = Metadata(**response.json())
    assert metadata.provenance.dataset_id == "sample_t2m"
    assert SAMPLE in metadata.provenance.product


def test_metadata_for_an_unknown_dataset_is_404(client):
    response = client.get("/api/v1/metadata", params={"dataset_id": "nope"})
    error = assert_error(response, 404, "dataset_not_found")
    assert error.details == {"dataset_id": "nope"}


def test_metadata_for_a_coming_soon_dataset_is_unavailable(client):
    # Listed in the catalogue but no processed files yet.
    response = client.get("/api/v1/metadata", params={"dataset_id": "sample_ndvi"})
    error = assert_error(response, 503, "data_unavailable")
    assert error.details["file"].endswith("provenance.json")


@pytest.mark.parametrize("params", [{}, {"dataset_id": "Not A Slug"}, {"dataset_id": "../etc"}])
def test_bad_metadata_parameters_are_422_invalid_parameter(client, params):
    error = assert_error(client.get("/api/v1/metadata", params=params), 422, "invalid_parameter")
    assert error.details["errors"][0]["parameter"] == "dataset_id"


@pytest.mark.parametrize(
    "path",
    ["/api/v1/catalogue", "/api/v1/regions", "/api/v1/metadata?dataset_id=sample_t2m"],
)
def test_missing_data_files_are_503_data_unavailable(empty_client, path):
    error = assert_error(empty_client.get(path), 503, "data_unavailable")
    assert error.details["reason"] == "file is missing"


def test_a_file_that_breaks_the_contract_is_503_not_a_crash(monkeypatch, tmp_path):
    (tmp_path / "catalogue.json").write_text('[{"dataset_id": "x"}]', encoding="utf-8")
    monkeypatch.setenv("TERRALENS_DATA_DIR", str(tmp_path))
    error = assert_error(TestClient(app).get("/api/v1/catalogue"), 503, "data_unavailable")
    assert error.details["reason"] == "does not match the contract"


def test_cors_allows_the_local_frontend(client):
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
