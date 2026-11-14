"""Tests for the contract builder (NAS-7, plus Kevin's review follow-ups)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from pipeline.build import (
    CONTRACT_COLUMNS,
    UnitMismatchError,
    build,
    contract_frame,
    trim_to_window,
    window_for,
)
from pipeline.registry import VARIABLES

SAMPLE = Path(__file__).parent / "data" / "giovanni_t2m_sample.csv"


def _monthly(values: list[float], start: str = "2000-01-01") -> pd.DataFrame:
    index = pd.date_range(start, periods=len(values), freq="MS")
    return pd.DataFrame({"timestamp": index, "value": values})


def _write_export(
    tmp_path: Path,
    rows: list[tuple[int, int, float | None]],
    *,
    unit: str | None = "K",
    name: str = "export.csv",
) -> Path:
    lines = ["# SAMPLE - NOT NASA DATA", "Parameter,T2M"]
    if unit is not None:
        lines.append(f"Unit,{unit}")
    lines.append("Month,Mean")
    lines.extend(
        f"{year}-{month:02d},{'' if value is None else value}" for year, month, value in rows
    )
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _kwargs(tmp_path: Path, **overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = dict(
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
    kwargs.update(overrides)
    return kwargs


def test_every_variable_carries_an_ordered_window() -> None:
    for variable_id, spec in VARIABLES.items():
        assert spec.start_year < spec.end_year, variable_id
        assert window_for(variable_id) == (spec.start_year, spec.end_year)


def test_t2m_window_starts_in_1981_not_1980() -> None:
    assert window_for("t2m") == (1981, 2025)


def test_window_drops_rows_before_its_start_year(tmp_path: Path) -> None:
    rows = [(1980, month, 280.0 + month) for month in range(1, 13)]
    rows += [(1981, month, 281.0 + month) for month in range(1, 13)]
    csv_path = _write_export(tmp_path, rows)

    parquet, _ = build(
        csv_path, region_id="ireland", **_kwargs(tmp_path, start_year=1981, end_year=1981)
    )
    frame = pd.read_parquet(parquet)

    assert len(frame) == 12
    assert frame["timestamp"].iloc[0] == pd.Timestamp("1981-01-01").date()
    assert frame["timestamp"].iloc[-1] == pd.Timestamp("1981-12-01").date()


def test_missing_months_stay_as_null_rows(tmp_path: Path) -> None:
    rows = [(1981, month, 280.0 + month) for month in range(1, 13)]
    rows += [(1982, month, 282.0 + month) for month in range(1, 13) if month != 3]
    csv_path = _write_export(tmp_path, rows)

    parquet, provenance = build(
        csv_path, region_id="ireland", **_kwargs(tmp_path, start_year=1981, end_year=1982)
    )
    frame = pd.read_parquet(parquet)

    assert len(frame) == 24, "the year with a gap must not be dropped"
    missing = frame[frame["timestamp"] == pd.Timestamp("1982-03-01").date()]
    assert len(missing) == 1
    assert pd.isna(missing["value"].iloc[0])

    payload = json.loads(provenance.read_text())
    assert payload["regions"]["ireland"]["observations"] == 23
    assert any("1 in this series" in line for line in payload["transformations"])


def test_trim_to_window_clips_edges_and_fills_gaps() -> None:
    frame = pd.concat(
        [
            _monthly([9.0], start="1999-11-01"),
            _monthly([4.0], start="2000-03-01"),
        ],
        ignore_index=True,
    )

    trimmed = trim_to_window(frame, start_year=2000, end_year=2000)

    assert len(trimmed) == 3, "1999 is clipped, 2000-01 and 2000-02 are null rows"
    assert trimmed["timestamp"].iloc[0] == pd.Timestamp("2000-01-01")
    assert trimmed["timestamp"].iloc[-1] == pd.Timestamp("2000-03-01")
    assert trimmed["value"].isna().sum() == 2
    assert trimmed["value"].iloc[-1] == pytest.approx(4.0)


def test_trim_to_window_rejects_a_window_with_no_values() -> None:
    frame = _monthly([1.0] * 12, start="1990-01-01")
    with pytest.raises(ValueError):
        trim_to_window(frame, start_year=2000, end_year=2000)


def test_unit_row_mismatch_stops_the_build(tmp_path: Path) -> None:
    rows = [(2001, 1, 0.2), (2001, 2, 0.3)]
    csv_path = _write_export(tmp_path, rows, unit="mm/month")

    with pytest.raises(UnitMismatchError) as error:
        build(
            csv_path,
            region_id="ireland",
            **_kwargs(
                tmp_path,
                variable_id="precipitation",
                dataset_id="gpm_3imergm_v07b",
                native_unit="mm/hr",
                output_unit="mm/month",
            ),
        )
    assert "mm/month" in str(error.value)
    assert "mm/hr" in str(error.value)


def test_unit_row_match_is_accepted(tmp_path: Path) -> None:
    rows = [(1981, month, 280.0 + month) for month in range(1, 13)]
    csv_path = _write_export(tmp_path, rows, unit="kelvin")

    parquet, provenance = build(
        csv_path, region_id="ireland", **_kwargs(tmp_path, start_year=1981, end_year=1981)
    )
    assert pd.read_parquet(parquet)["value"].iloc[0] == pytest.approx(7.85)
    transformations = json.loads(provenance.read_text())["transformations"]
    assert any("'kelvin'" in line and "matched" in line for line in transformations)


def test_a_missing_unit_row_is_tolerated(tmp_path: Path) -> None:
    rows = [(1981, month, 280.0 + month) for month in range(1, 13)]
    csv_path = _write_export(tmp_path, rows, unit=None)

    _, provenance = build(
        csv_path, region_id="ireland", **_kwargs(tmp_path, start_year=1981, end_year=1981)
    )
    transformations = json.loads(provenance.read_text())["transformations"]
    assert any("declared no unit" in line for line in transformations)


def test_a_series_that_stops_early_is_rejected(tmp_path: Path) -> None:
    rows = [(1981, month, 280.0 + month) for month in range(1, 7)]
    csv_path = _write_export(tmp_path, rows)

    with pytest.raises(ValueError, match="allow-short"):
        build(csv_path, region_id="ireland", **_kwargs(tmp_path, start_year=1981, end_year=1981))


def test_allow_short_pads_the_window_and_records_it(tmp_path: Path) -> None:
    rows = [(1981, month, 280.0 + month) for month in range(1, 7)]
    csv_path = _write_export(tmp_path, rows)

    parquet, provenance = build(
        csv_path,
        region_id="ireland",
        **_kwargs(tmp_path, start_year=1981, end_year=1981, allow_short=True),
    )
    frame = pd.read_parquet(parquet)

    assert len(frame) == 12, "the window is still the shape of the series"
    assert frame["value"].isna().sum() == 6, "the six absent months are null rows"
    transformations = json.loads(provenance.read_text())["transformations"]
    assert any("short series allowed" in line for line in transformations)


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
    assert frame["n_valid_days"].isna().all()
    assert frame["unit"].iloc[0] == "°C"
    assert str(frame["valid_cell_count"].dtype) == "Int64"
    assert str(frame["n_valid_days"].dtype) == "Int64"


def test_build_writes_parquet_and_merges_provenance(tmp_path: Path) -> None:
    kwargs = _kwargs(tmp_path, start_year=1981, end_year=1982)

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
    assert payload["period_start"] == "1981-01-01"
    assert payload["period_end"] == "1982-12-01"
    assert payload["regions"]["iberia"]["observations"] == 24
    assert len(payload["regions"]["ireland"]["source_csv_sha256"]) == 64
    assert set(payload) <= {
        "dataset_id",
        "product",
        "version",
        "doi_or_url",
        "access_date",
        "access_route",
        "variable_field",
        "scale_factor",
        "native_unit",
        "output_unit",
        "spatial_resolution",
        "period_start",
        "period_end",
        "qa_rules",
        "region_source",
        "transformations",
        "regions",
    }, "no key may be added that the backend contract does not know"
