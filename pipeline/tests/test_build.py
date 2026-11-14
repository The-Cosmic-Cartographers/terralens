"""Tests for the contract builder (NAS-7)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from pipeline.build import (
    CONTRACT_COLUMNS,
    build,
    complete_years,
    contract_frame,
    trim_to_complete_years,
)

SAMPLE = Path(__file__).parent / "data" / "giovanni_t2m_sample.csv"


def _monthly(values: list[float], start: str = "2000-01-01") -> pd.DataFrame:
    index = pd.date_range(start, periods=len(values), freq="MS")
    return pd.DataFrame({"timestamp": index, "value": values})


def test_complete_years_ignores_partial_years() -> None:
    frame = _monthly([1.0] * 12 + [2.0] * 12 + [3.0] * 5)
    assert complete_years(frame) == [2000, 2001]


def test_trim_drops_partial_first_and_last_years() -> None:
    frame = _monthly([1.0] * 60, start="1998-08-01")
    trimmed = trim_to_complete_years(frame)
    assert trimmed["timestamp"].iloc[0] == pd.Timestamp("1999-01-01")
    assert trimmed["timestamp"].iloc[-1] == pd.Timestamp("2002-12-01")


def test_trim_respects_an_explicit_end_year() -> None:
    frame = _monthly([1.0] * 36)
    trimmed = trim_to_complete_years(frame, end_year=2001)
    assert trimmed["timestamp"].dt.year.max() == 2001


def test_trim_rejects_an_end_year_beyond_the_data() -> None:
    frame = _monthly([1.0] * 24)
    with pytest.raises(ValueError):
        trim_to_complete_years(frame, end_year=2030)


def test_contract_frame_has_every_contract_column_in_order() -> None:
    frame = contract_frame(
        _monthly([1.0, 2.0]),
        dataset_id="merra2_m2tmnxslv",
        variable_id="t2m",
        region_id="ireland",
        unit="°C",
        source="MERRA-2 M2TMNXSLV v5.12.4",
    )
    assert list(frame.columns) == CONTRACT_COLUMNS
    assert frame["anomaly"].isna().all()
    assert frame["coverage_fraction"].isna().all()
    assert frame["unit"].iloc[0] == "°C"
    assert str(frame["valid_cell_count"].dtype) == "Int64"


def test_build_writes_parquet_and_merges_provenance(tmp_path: Path) -> None:
    kwargs = dict(
        dataset_id="merra2_m2tmnxslv",
        variable_id="t2m",
        product="MERRA-2 2 m air temperature",
        version="5.12.4",
        native_unit="K",
        output_unit="°C",
        spatial_resolution="0.5° x 0.625°",
        giovanni_variable_id="T2M",
        requested_box="-10.5,51.4,-6.0,55.4",
        analyzable_region="51.4N-55.4N, 10.5W-6W",
        permalink="https://giovanni.gsfc.nasa.gov/example",
        access_date="2026-11-14",
        start_year=None,
        end_year=None,
        out_root=tmp_path,
    )

    parquet, provenance = build(SAMPLE, region_id="ireland", **kwargs)
    assert parquet.exists()
    frame = pd.read_parquet(parquet)
    assert len(frame) == 24
    assert frame["value"].iloc[0] == pytest.approx(10.0)
    assert frame["timestamp"].iloc[0] == pd.Timestamp("1981-01-01").date()

    build(SAMPLE, region_id="iberia", **kwargs)
    payload = json.loads(provenance.read_text())
    assert set(payload["regions"]) == {"ireland", "iberia"}
    assert payload["output_unit"] == "°C"
    assert payload["regions"]["iberia"]["observations"] == 24
    assert len(payload["regions"]["ireland"]["source_csv_sha256"]) == 64
