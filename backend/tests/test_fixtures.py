"""The SAMPLE fixtures must validate against the doc 04 models, show every UI
state, and match what the generator produces (so nobody hand-edits them)."""

import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from app.models import (
    CatalogueItem,
    CompareResult,
    Lineup,
    Metadata,
    Provenance,
    Region,
    SeriesResponse,
    SeriesRow,
    TrendResult,
    Windows,
)
from scripts.generate_fixtures import REGIONS, SAMPLE, generate

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_ids() -> list[str]:
    return [i["dataset_id"] for i in load(FIXTURES / "catalogue.json") if i["status"] == "ready"]


def test_data_version_says_sample():
    assert SAMPLE in (FIXTURES / "data_version.txt").read_text(encoding="utf-8")


def test_catalogue_and_regions_validate():
    catalogue = [CatalogueItem(**i) for i in load(FIXTURES / "catalogue.json")]
    assert {c.status for c in catalogue} == {"ready", "coming_soon"}
    regions = [Region(**r) for r in load(FIXTURES / "regions.json")]
    assert [r.region_id for r in regions] == [r.region_id for r in REGIONS]


@pytest.mark.parametrize("dataset_id", dataset_ids())
@pytest.mark.parametrize("region_id", [r.region_id for r in REGIONS])
def test_series_validate_and_are_marked_sample(dataset_id, region_id):
    table = pq.read_table(FIXTURES / "processed" / dataset_id / f"{region_id}.parquet")
    rows = [SeriesRow(**r) for r in table.to_pylist()]
    assert rows
    assert all(SAMPLE in r.source for r in rows)
    months = [(r.timestamp.year, r.timestamp.month) for r in rows]
    assert months == sorted(set(months)), "one row per month, in order"
    first, last = rows[0], rows[-1]
    assert len(rows) == (last.timestamp.year - first.timestamp.year) * 12 + 12
    response = SeriesResponse(
        dataset_id=dataset_id,
        variable_id=first.variable_id,
        region_id=region_id,
        unit=first.unit,
        rows=rows,
    )
    assert response.rows


@pytest.mark.parametrize("dataset_id", dataset_ids())
def test_provenance_metadata_and_trends_validate(dataset_id):
    provenance = Provenance(**load(FIXTURES / "processed" / dataset_id / "provenance.json"))
    assert SAMPLE in provenance.product
    extras = load(FIXTURES / "metadata" / f"{dataset_id}.json")
    assert Metadata(dataset_id=dataset_id, provenance=provenance, **extras)

    trends = [TrendResult(**t) for t in load(FIXTURES / "results" / dataset_id / "trends.json")]
    assert [t.region_id for t in trends] == [r.region_id for r in REGIONS]
    compare = CompareResult(
        dataset_id=dataset_id,
        variable_id=trends[0].variable_id,
        period_start=trends[0].period_start,
        period_end=trends[0].period_end,
        bh_family=trends[0].bh_family,
        results=trends,
    )
    assert compare.period_note is None


@pytest.mark.parametrize("region_id", [r.region_id for r in REGIONS])
def test_lineup_validates_and_uses_catalogue_datasets(region_id):
    lineup = Lineup(**load(FIXTURES / "results" / "lineup" / f"{region_id}.json"))
    assert {row.dataset_id for row in lineup.rows} == set(dataset_ids())


@pytest.mark.parametrize("dataset_id", dataset_ids())
@pytest.mark.parametrize("region_id", [r.region_id for r in REGIONS])
def test_windows_validate(dataset_id, region_id):
    path = FIXTURES / "results" / "windows" / dataset_id / f"{region_id}.json"
    windows = Windows(**load(path))
    assert (windows.dataset_id, windows.region_id) == (dataset_id, region_id)
    assert windows.windows


def test_every_ui_state_is_present():
    rows = [
        row
        for region in REGIONS
        for row in Lineup(**load(FIXTURES / "results" / "lineup" / f"{region.region_id}.json")).rows
    ]
    assert {row.trend.verdict for row in rows} == {
        "significant",
        "weak_evidence",
        "no_clear_trend",
        "not_enough_data",
    }
    assert {row.trend.trend_direction for row in rows} == {
        "increasing",
        "decreasing",
        "no_significant_trend",
        "withheld",
    }
    assert {row.product_type for row in rows} == {"reanalysis", "land_model", "satellite"}
    trends = {
        t["region_id"]: t
        for t in load(FIXTURES / "results" / "sample_precipitation" / "trends.json")
    }
    assert trends["ireland"]["trend_direction"] == "increasing"
    assert trends["iberia"]["trend_direction"] == "decreasing"


def test_committed_fixtures_match_the_generator(tmp_path):
    generate(tmp_path)
    expected = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    committed = sorted(
        p.relative_to(FIXTURES)
        for p in FIXTURES.rglob("*")
        if p.is_file() and p.name != "README.md"
    )
    assert committed == expected
    for path in expected:
        if path.suffix == ".parquet":
            assert (
                pq.read_table(FIXTURES / path).to_pylist()
                == pq.read_table(tmp_path / path).to_pylist()
            )
        else:
            assert (FIXTURES / path).read_text(encoding="utf-8") == (tmp_path / path).read_text(
                encoding="utf-8"
            ), f"{path} was edited by hand; regenerate it"
