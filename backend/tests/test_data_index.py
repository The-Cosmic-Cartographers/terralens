"""The index builder turns processed series into the files the API needs."""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from pipeline.regions import load_regions
from pipeline.registry import VARIABLES
from scripts.build_data_index import build

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


@pytest.fixture
def index(tmp_path, monkeypatch):
    out = tmp_path / "data"
    shutil.copytree(PROCESSED, out / "processed")
    build(out / "processed", out)
    monkeypatch.setenv("TERRALENS_DATA_DIR", str(out))
    return TestClient(app), out


def test_every_dataset_id_in_the_registry_is_unique():
    ids = [spec.dataset_id for spec in VARIABLES.values()]
    assert len(set(ids)) == len(ids)


def _pulled_dataset_ids(processed: Path) -> set[str]:
    """Datasets the builder should mark ready: series plus provenance on disk."""
    return {
        spec.dataset_id
        for spec in VARIABLES.values()
        if (processed / spec.dataset_id / "provenance.json").is_file()
        and list((processed / spec.dataset_id).glob("*.parquet"))
    }


def test_catalogue_marks_pulled_datasets_ready_and_the_rest_coming_soon(index):
    client, out = index
    items = {i["dataset_id"]: i["status"] for i in client.get("/api/v1/catalogue").json()}
    expected_ready = _pulled_dataset_ids(out / "processed")

    assert {dataset for dataset, status in items.items() if status == "ready"} == expected_ready
    assert set(items) == {spec.dataset_id for spec in VARIABLES.values()}
    assert items["merra2_m2tmnxslv"] == "ready"


def test_regions_are_only_those_with_a_series(index):
    client, out = index
    ids = [r["region_id"] for r in client.get("/api/v1/regions").json()]
    expected = {path.stem for path in (out / "processed").glob("*/*.parquet")}

    # The builder sorts by the registry's region order, so compare both ways.
    assert ids == [region_id for region_id in load_regions() if region_id in expected]
    assert set(ids) == expected


def test_real_series_and_metadata_are_served(index):
    client, out = index
    series = client.get("/api/v1/regions/sahel/series", params={"dataset_id": "merra2_m2tmnxslv"})
    assert series.status_code == 200
    assert len(series.json()["rows"]) == 540
    meta = client.get("/api/v1/metadata", params={"dataset_id": "merra2_m2tmnxslv"})
    assert meta.status_code == 200
    expected = {
        path.stem for path in (out / "processed" / "merra2_m2tmnxslv").glob("*.parquet")
    }
    assert set(meta.json()["provenance"]["regions"]) == expected


def test_data_version_is_not_sample(index):
    client, _ = index
    version = client.get("/health").json()["data_version"]
    assert version.startswith("giovanni-") and "SAMPLE" not in version


def test_the_output_is_reproducible(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    build(PROCESSED, first)
    build(PROCESSED, second)
    for name in ("catalogue.json", "regions.json", "data_version.txt"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
