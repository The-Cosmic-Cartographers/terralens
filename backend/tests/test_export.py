"""The static export must equal the API, refuse SAMPLE data by default, and never
ship a snapshot with holes."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.export import ExportError, export, main
from app.main import app

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def snapshot(tmp_path):
    out = tmp_path / "public" / "data"
    written = export(FIXTURES, out, allow_sample=True)
    return out, written


def test_every_file_equals_the_api_response(snapshot, monkeypatch):
    out, written = snapshot
    monkeypatch.setenv("TERRALENS_DATA_DIR", str(FIXTURES))
    client = TestClient(app)

    assert read(out / "health.json") == client.get("/health").json()
    assert read(out / "catalogue.json") == client.get("/api/v1/catalogue").json()
    assert read(out / "regions.json") == client.get("/api/v1/regions").json()

    checked = 3
    for region in ("ireland", "iberia"):
        assert (
            read(out / "lineup" / f"{region}.json")
            == client.get(f"/api/v1/regions/{region}/lineup").json()
        )
        checked += 1
    for item in client.get("/api/v1/catalogue").json():
        if item["status"] != "ready":
            continue
        dataset = item["dataset_id"]
        meta = client.get("/api/v1/metadata", params={"dataset_id": dataset}).json()
        assert read(out / "metadata" / f"{dataset}.json") == meta
        checked += 1
        for region in ("ireland", "iberia"):
            for kind in ("series", "trend", "windows"):
                response = client.get(
                    f"/api/v1/regions/{region}/{kind}", params={"dataset_id": dataset}
                )
                assert read(out / kind / dataset / f"{region}.json") == response.json()
                checked += 1
    assert checked == len(written)  # nothing extra, nothing missing


def test_the_snapshot_carries_the_data_version(snapshot):
    out, _ = snapshot
    assert "SAMPLE" in read(out / "health.json")["data_version"]


def test_sample_data_is_refused_without_the_flag(tmp_path):
    out = tmp_path / "data"
    with pytest.raises(ExportError, match="SAMPLE"):
        export(FIXTURES, out)
    assert not out.exists()


def test_cli_returns_1_for_sample_data_and_0_with_the_flag(tmp_path, capsys):
    out = tmp_path / "data"
    assert main(["--data-dir", str(FIXTURES), "--out", str(out)]) == 1
    assert "SAMPLE" in capsys.readouterr().err
    assert main(["--data-dir", str(FIXTURES), "--out", str(out), "--allow-sample"]) == 0
    assert "wrote" in capsys.readouterr().out


def test_a_missing_file_stops_the_export_and_writes_nothing(tmp_path):
    root = tmp_path / "data"
    shutil.copytree(FIXTURES, root)
    (root / "processed" / "sample_t2m" / "iberia.parquet").unlink()
    out = tmp_path / "out"
    with pytest.raises(ExportError, match="series/sample_t2m/iberia.json"):
        export(root, out, allow_sample=True)
    assert not out.exists()


def test_a_failed_export_leaves_an_existing_snapshot_alone(snapshot, tmp_path):
    out, _ = snapshot
    before = read(out / "catalogue.json")
    root = tmp_path / "data"
    shutil.copytree(FIXTURES, root)
    (root / "regions.json").unlink()
    with pytest.raises(Exception, match="regions.json"):
        export(root, out, allow_sample=True)
    assert read(out / "catalogue.json") == before


def test_export_is_reproducible_and_only_touches_its_own_files(tmp_path):
    out = tmp_path / "data"
    out.mkdir()
    (out / "keep.txt").write_text("not mine", encoding="utf-8")
    (out / "series").mkdir()
    (out / "series" / "stale.json").write_text("{}", encoding="utf-8")

    export(FIXTURES, out, allow_sample=True)
    first = {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    export(FIXTURES, out, allow_sample=True)
    second = {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}

    assert first == second
    assert (out / "keep.txt").read_text(encoding="utf-8") == "not mine"
    assert not (out / "series" / "stale.json").exists()  # stale generated files are removed
