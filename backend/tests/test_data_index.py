"""The index builder turns processed series into the files the API needs."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from pipeline.registry import VARIABLES
from scripts.build_data_index import APP_REGIONS, build

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


def has_all_app_regions(dataset_id):
    folder = PROCESSED / dataset_id
    return set(APP_REGIONS) <= {path.stem for path in folder.glob("*.parquet")}


def test_a_dataset_is_ready_only_when_it_covers_every_app_region(index):
    """Readiness follows the processed folder and the explicit app regions (D26).

    A dataset with a series for only some of the app regions would leave holes in a
    static export, so it stays coming soon. Which datasets are ready is not asserted
    as a fixed list, so adding a row cannot break this test.
    """
    client, _ = index
    items = {i["dataset_id"]: i["status"] for i in client.get("/api/v1/catalogue").json()}
    assert len(items) == len(VARIABLES)
    for spec in VARIABLES.values():
        expected = "ready" if has_all_app_regions(spec.dataset_id) else "coming_soon"
        assert items[spec.dataset_id] == expected, spec.dataset_id
    assert items["merra2_m2tmnxslv"] == "ready"


def test_regions_are_exactly_the_app_regions(index):
    """Extra regions or city pairs on disk (Iberia, the NO2 cities) never reach the app."""
    client, _ = index
    ids = [r["region_id"] for r in client.get("/api/v1/regions").json()]
    assert ids == list(APP_REGIONS)


def test_a_dataset_missing_one_app_region_is_coming_soon(tmp_path):
    out = tmp_path / "data"
    shutil.copytree(PROCESSED, out / "processed")
    (out / "processed" / "merra2_m2tmnxslv" / "sahel.parquet").unlink()
    build(out / "processed", out)
    items = {
        item["dataset_id"]: item["status"]
        for item in json.loads((out / "catalogue.json").read_text(encoding="utf-8"))
    }
    assert items["merra2_m2tmnxslv"] == "coming_soon"
    assert not (out / "metadata" / "merra2_m2tmnxslv.json").exists()


def test_an_extra_region_on_disk_does_not_change_the_output(tmp_path):
    base, extra = tmp_path / "base", tmp_path / "extra"
    build(PROCESSED, base)
    processed = tmp_path / "processed"
    shutil.copytree(PROCESSED, processed)
    dataset = processed / "merra2_m2tmnxslv"
    shutil.copy(dataset / "ireland.parquet", dataset / "iberia.parquet")
    build(processed, extra)
    for name in ("regions.json", "catalogue.json"):
        assert (base / name).read_bytes() == (extra / name).read_bytes()


def test_real_series_and_metadata_are_served(index):
    client, _ = index
    series = client.get("/api/v1/regions/sahel/series", params={"dataset_id": "merra2_m2tmnxslv"})
    assert series.status_code == 200
    assert len(series.json()["rows"]) == 540
    meta = client.get("/api/v1/metadata", params={"dataset_id": "merra2_m2tmnxslv"})
    assert meta.status_code == 200
    assert set(APP_REGIONS) <= set(meta.json()["provenance"]["regions"])


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
