"""What the real pipeline writes is served by the real API (the NAS-7 / NAS-16 seam)."""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Metadata, SeriesResponse
from pipeline.build import main as build_main

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"
SAMPLE_CSV = (
    Path(__file__).resolve().parents[2]
    / "pipeline"
    / "tests"
    / "data"
    / ("giovanni_t2m_sample.csv")
)


@pytest.fixture
def client_and_root(monkeypatch, tmp_path):
    root = tmp_path / "data"
    shutil.copytree(FIXTURES, root)
    monkeypatch.setenv("TERRALENS_DATA_DIR", str(root))
    return TestClient(app), root


def test_pipeline_output_is_served_by_the_api(client_and_root):
    client, root = client_and_root
    # Overwrite the fixture series with pipeline output for the same dataset and region.
    code = build_main(
        [
            str(SAMPLE_CSV),
            "--variable-id", "t2m",
            "--region-id", "ireland",
            "--dataset-id", "sample_t2m",
            "--analyzable-region", "n/a (test)",
            "--permalink", "https://example.invalid/sample",
            "--out", str(root / "processed"),
        ]
    )  # fmt: skip
    assert code == 0

    series = client.get("/api/v1/regions/ireland/series", params={"dataset_id": "sample_t2m"})
    assert series.status_code == 200, series.text
    body = SeriesResponse(**series.json())
    assert body.rows and all(row.coverage_fraction is None for row in body.rows)
    assert body.unit == "°C"

    meta = client.get("/api/v1/metadata", params={"dataset_id": "sample_t2m"})
    assert meta.status_code == 200, meta.text
    regions = Metadata(**meta.json()).provenance.regions
    assert regions["ireland"].source_csv == "giovanni_t2m_sample.csv"
    assert regions["ireland"].analyzable_region == "n/a (test)"
    assert "iberia" in regions  # the earlier region's entry is kept when another is merged in
