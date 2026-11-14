"""Files shaped like the pipeline's real output (Giovanni: no per-cell counts) are served."""

import json
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Metadata, SeriesResponse

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"
COVERAGE = ("valid_cell_count", "total_cell_count", "coverage_fraction")


@pytest.fixture
def client_and_root(monkeypatch, tmp_path):
    root = tmp_path / "data"
    shutil.copytree(FIXTURES, root)
    monkeypatch.setenv("TERRALENS_DATA_DIR", str(root))
    return TestClient(app), root


def null_the_coverage(path: Path) -> None:
    table = pq.read_table(path)
    for name in COVERAGE:
        column = table.schema.field(name)
        table = table.set_column(
            table.schema.get_field_index(name), column, pa.nulls(len(table), column.type)
        )
    pq.write_table(table, path)


def test_series_with_null_coverage_is_served(client_and_root):
    client, root = client_and_root
    null_the_coverage(root / "processed" / "sample_t2m" / "ireland.parquet")
    response = client.get("/api/v1/regions/ireland/series", params={"dataset_id": "sample_t2m"})
    assert response.status_code == 200, response.text
    rows = SeriesResponse(**response.json()).rows
    assert all(row.coverage_fraction is None and row.valid_cell_count is None for row in rows)


def test_series_without_the_coverage_columns_is_served(client_and_root):
    client, root = client_and_root
    path = root / "processed" / "sample_t2m" / "ireland.parquet"
    pq.write_table(pq.read_table(path).drop_columns(list(COVERAGE)), path)
    response = client.get("/api/v1/regions/ireland/series", params={"dataset_id": "sample_t2m"})
    assert response.status_code == 200, response.text


def test_metadata_serves_per_region_provenance(client_and_root):
    client, _ = client_and_root
    response = client.get("/api/v1/metadata", params={"dataset_id": "sample_t2m"})
    assert response.status_code == 200
    provenance = Metadata(**response.json()).provenance
    assert set(provenance.regions) == {"ireland", "iberia"}


def test_the_old_flat_provenance_layout_is_a_503(client_and_root):
    client, root = client_and_root
    path = root / "processed" / "sample_t2m" / "provenance.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record.pop("regions")
    record["requested_box"] = "-10.5,51.4,-6.0,55.4"
    path.write_text(json.dumps(record), encoding="utf-8")
    response = client.get("/api/v1/metadata", params={"dataset_id": "sample_t2m"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "data_unavailable"
