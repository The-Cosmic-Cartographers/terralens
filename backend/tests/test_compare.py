"""GET /api/v1/compare (schema 3) against the SAMPLE fixtures."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import CompareResult, ErrorResponse

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"
READY = [
    item["dataset_id"]
    for item in json.loads((FIXTURES / "catalogue.json").read_text(encoding="utf-8"))
    if item["status"] == "ready"
]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TERRALENS_DATA_DIR", str(FIXTURES))
    return TestClient(app)


@pytest.fixture
def copy_client(monkeypatch, tmp_path):
    root = tmp_path / "data"
    shutil.copytree(FIXTURES, root)
    monkeypatch.setenv("TERRALENS_DATA_DIR", str(root))
    return TestClient(app), root


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    assert ErrorResponse(**response.json()).error.code == code
    return response.json()["error"]


def edit_trends(root, dataset_id, change):
    path = root / "results" / dataset_id / "trends.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    change(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.parametrize("dataset_id", READY)
def test_compare_returns_every_region_in_the_compare_family(client, dataset_id):
    response = client.get("/api/v1/compare", params={"dataset_id": dataset_id})
    assert response.status_code == 200
    body = CompareResult(**response.json())
    assert [r.region_id for r in body.results] == ["ireland", "iberia"]
    assert body.bh_family == f"compare:{body.variable_id}"
    assert body.period_start <= body.period_end


def test_compare_keeps_regions_json_order_whatever_the_file_order(copy_client):
    client, root = copy_client
    edit_trends(root, "sample_t2m", lambda p: p.reverse())
    body = client.get("/api/v1/compare", params={"dataset_id": "sample_t2m"}).json()
    assert [r["region_id"] for r in body["results"]] == ["ireland", "iberia"]


def test_matching_periods_have_no_note(client):
    body = client.get("/api/v1/compare", params={"dataset_id": "sample_t2m"}).json()
    assert body["period_note"] is None


def test_differing_periods_report_the_overlap_and_say_so(copy_client):
    client, root = copy_client

    def shorten(payload):
        payload[1]["period_start"] = "1990-01-01"
        payload[1]["period_end"] = "2020-12-01"

    edit_trends(root, "sample_t2m", shorten)
    body = client.get("/api/v1/compare", params={"dataset_id": "sample_t2m"}).json()
    assert (body["period_start"], body["period_end"]) == ("1990-01-01", "2020-12-01")
    assert "not on the same period" in body["period_note"]
    assert "iberia 1990-01 to 2020-12" in body["period_note"]


def test_the_compare_adjustment_can_differ_from_the_lineup_one(client):
    # Different BH families: the compare file is read as written, not copied from the lineup.
    compare = client.get("/api/v1/compare", params={"dataset_id": "sample_t2m"}).json()
    lineup = client.get("/api/v1/regions/ireland/lineup").json()
    row = next(r for r in lineup["rows"] if r["dataset_id"] == "sample_t2m")
    result = next(r for r in compare["results"] if r["region_id"] == "ireland")
    assert result["bh_family"] == "compare:t2m"
    assert row["trend"]["bh_family"] == "lineup:ireland"


def test_unknown_dataset_is_404(client):
    error = assert_error(
        client.get("/api/v1/compare", params={"dataset_id": "nope"}), 404, "dataset_not_found"
    )
    assert error["details"] == {"dataset_id": "nope"}


def test_missing_dataset_id_is_422(client):
    error = assert_error(client.get("/api/v1/compare"), 422, "invalid_parameter")
    assert error["details"]["errors"][0]["parameter"] == "dataset_id"


def test_a_coming_soon_dataset_is_503(client):
    response = client.get("/api/v1/compare", params={"dataset_id": "sample_ndvi"})
    error = assert_error(response, 503, "data_unavailable")
    assert error["details"]["reason"] == "file is missing"


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.clear(),
        lambda p: p.append(dict(p[0])),  # a region twice
        lambda p: p[0].update(region_id="atlantis"),
        lambda p: p[0].update(dataset_id="sample_aerosol"),
        lambda p: p[0].update(bh_family="compare:other"),
        lambda p: (p[0].update(period_start="2030-01-01", period_end="2031-01-01"),),  # no overlap
    ],
    ids=["empty", "duplicate", "unknown-region", "wrong-dataset", "wrong-family", "no-overlap"],
)
def test_files_that_break_the_contract_are_503(copy_client, change):
    client, root = copy_client
    edit_trends(root, "sample_t2m", change)
    response = client.get("/api/v1/compare", params={"dataset_id": "sample_t2m"})
    error = assert_error(response, 503, "data_unavailable")
    assert error["details"]["reason"] == "does not match the contract"
