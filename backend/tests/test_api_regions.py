"""API v1 part B (series, trend, lineup, windows) against the SAMPLE fixtures."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ErrorResponse, Lineup, SeriesResponse, TrendResult, Windows

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"
REGIONS = ["ireland", "iberia"]
READY = [
    item["dataset_id"]
    for item in json.loads((FIXTURES / "catalogue.json").read_text(encoding="utf-8"))
    if item["status"] == "ready"
]
BASE = "/api/v1/regions"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TERRALENS_DATA_DIR", str(FIXTURES))
    return TestClient(app)


@pytest.fixture
def copy_client(monkeypatch, tmp_path):
    """A writable copy of the fixtures, to break files on purpose."""
    root = tmp_path / "data"
    shutil.copytree(FIXTURES, root)
    monkeypatch.setenv("TERRALENS_DATA_DIR", str(root))
    return TestClient(app), root


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    error = ErrorResponse(**response.json()).error
    assert error.code == code
    return error


@pytest.mark.parametrize("dataset_id", READY)
@pytest.mark.parametrize("region_id", REGIONS)
def test_series_trend_and_windows_for_every_fixture(client, region_id, dataset_id):
    params = {"dataset_id": dataset_id}

    series = client.get(f"{BASE}/{region_id}/series", params=params)
    assert series.status_code == 200
    body = SeriesResponse(**series.json())
    assert (body.dataset_id, body.region_id) == (dataset_id, region_id)
    assert body.rows[0].unit == body.unit

    trend = client.get(f"{BASE}/{region_id}/trend", params=params)
    assert trend.status_code == 200
    assert TrendResult(**trend.json()).region_id == region_id

    windows = client.get(f"{BASE}/{region_id}/windows", params=params)
    assert windows.status_code == 200
    assert Windows(**windows.json()).windows


@pytest.mark.parametrize("region_id", REGIONS)
def test_lineup_is_the_ranked_board_and_trend_matches_it(client, region_id):
    response = client.get(f"{BASE}/{region_id}/lineup")
    assert response.status_code == 200
    lineup = Lineup(**response.json())
    assert len(lineup.rows) == 5
    # The detail card must show exactly what the board shows.
    for row in lineup.rows:
        trend = client.get(f"{BASE}/{region_id}/trend", params={"dataset_id": row.dataset_id})
        assert TrendResult(**trend.json()) == row.trend


def test_a_withheld_result_is_200_with_withheld_direction(client):
    params = {"dataset_id": "sample_aerosol"}
    trend = client.get(f"{BASE}/iberia/trend", params=params)
    assert trend.status_code == 200
    body = trend.json()
    assert body["trend_direction"] == "withheld"
    assert body["verdict"] == "not_enough_data"
    assert body["p_value"] is None and body["withheld_reason"]

    series = SeriesResponse(**client.get(f"{BASE}/iberia/series", params=params).json())
    assert any(row.value is None for row in series.rows)  # months withheld for low coverage

    windows = Windows(**client.get(f"{BASE}/iberia/windows", params=params).json())
    assert {w.verdict for w in windows.windows} == {"not_enough_data"}


@pytest.mark.parametrize(
    "path",
    [
        "series?dataset_id=sample_t2m",
        "trend?dataset_id=sample_t2m",
        "lineup",
        "windows?dataset_id=sample_t2m",
    ],
)
def test_unknown_region_is_404_region_not_found(client, path):
    error = assert_error(client.get(f"{BASE}/atlantis/{path}"), 404, "region_not_found")
    assert error.details == {"region_id": "atlantis"}


@pytest.mark.parametrize("endpoint", ["series", "trend", "windows"])
def test_unknown_dataset_is_404_dataset_not_found(client, endpoint):
    response = client.get(f"{BASE}/ireland/{endpoint}", params={"dataset_id": "nope"})
    error = assert_error(response, 404, "dataset_not_found")
    assert error.details == {"dataset_id": "nope"}


@pytest.mark.parametrize("endpoint", ["series", "trend", "windows"])
def test_missing_dataset_id_is_422_invalid_parameter(client, endpoint):
    error = assert_error(client.get(f"{BASE}/ireland/{endpoint}"), 422, "invalid_parameter")
    assert error.details["errors"][0]["parameter"] == "dataset_id"


@pytest.mark.parametrize("endpoint", ["series?dataset_id=sample_t2m", "lineup"])
def test_a_bad_region_slug_is_422_invalid_parameter(client, endpoint):
    response = client.get(f"{BASE}/Bad Region/{endpoint}")
    error = assert_error(response, 422, "invalid_parameter")
    assert error.details["errors"][0]["parameter"] == "region_id"


@pytest.mark.parametrize("endpoint", ["series", "windows"])
def test_a_coming_soon_dataset_is_503_data_unavailable(client, endpoint):
    # Listed in the catalogue, but no processed files exist for it yet.
    response = client.get(f"{BASE}/ireland/{endpoint}", params={"dataset_id": "sample_ndvi"})
    error = assert_error(response, 503, "data_unavailable")
    assert error.details["reason"] == "file is missing"


def test_a_coming_soon_dataset_has_no_lineup_row_so_trend_is_503(client):
    response = client.get(f"{BASE}/ireland/trend", params={"dataset_id": "sample_ndvi"})
    error = assert_error(response, 503, "data_unavailable")
    assert "no lineup row" in error.details["reason"]


def test_an_empty_data_folder_is_503_not_a_crash(monkeypatch, tmp_path):
    monkeypatch.setenv("TERRALENS_DATA_DIR", str(tmp_path))
    client = TestClient(app)
    for path in ("ireland/lineup", "ireland/series?dataset_id=sample_t2m"):
        assert_error(client.get(f"{BASE}/{path}"), 503, "data_unavailable")


def test_a_corrupt_parquet_file_is_503(copy_client):
    client, root = copy_client
    (root / "processed" / "sample_t2m" / "ireland.parquet").write_bytes(b"not a parquet file")
    response = client.get(f"{BASE}/ireland/series", params={"dataset_id": "sample_t2m"})
    error = assert_error(response, 503, "data_unavailable")
    assert error.details["reason"] == "not a readable Parquet file"


def test_files_that_break_the_contract_are_503(copy_client):
    client, root = copy_client
    lineup = root / "results" / "lineup" / "ireland.json"
    payload = json.loads(lineup.read_text(encoding="utf-8"))
    payload["rows"][0]["trend"]["verdict"] = "significant"
    payload["rows"][0]["trend"]["adjusted_p_value"] = 0.9  # contradicts the verdict
    lineup.write_text(json.dumps(payload), encoding="utf-8")
    error = assert_error(client.get(f"{BASE}/ireland/lineup"), 503, "data_unavailable")
    assert error.details["reason"] == "does not match the contract"

    windows = root / "results" / "windows" / "sample_t2m" / "iberia.json"
    windows.write_text(windows.read_text(encoding="utf-8").replace('"iberia"', '"ireland"'))
    response = client.get(f"{BASE}/iberia/windows", params={"dataset_id": "sample_t2m"})
    assert_error(response, 503, "data_unavailable")


def test_a_lineup_file_for_the_wrong_region_is_503(copy_client):
    client, root = copy_client
    shutil.copy(root / "results/lineup/iberia.json", root / "results/lineup/ireland.json")
    assert_error(client.get(f"{BASE}/ireland/lineup"), 503, "data_unavailable")
