"""Tests for the OPeNDAP NO2 route (no network).

The payloads here are real NetCDF3 files written with scipy, so the parsing and
footprint maths are exercised against the same container the service returns.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline import no2, omi
from pipeline.giovanni import read_giovanni_csv, read_giovanni_unit
from pipeline.registry import VARIABLES

DUBLIN = (-6.5, 53.25, -6.0, 53.45)
DELHI = (76.5, 28.0, 78.0, 29.5)


def _payload(values: np.ndarray, fill: float = -1.2676506e30) -> bytes:
    """Write a one-field NetCDF3 file, the shape OPeNDAP's `.nc` returns."""
    from scipy.io import netcdf_file

    buffer = io.BytesIO()
    handle = netcdf_file(buffer, mode="w")
    handle.createDimension("YDim", values.shape[0])
    handle.createDimension("XDim", values.shape[1])
    field = handle.createVariable("field", "f", ("YDim", "XDim"))
    field._FillValue = np.float32(fill)
    field[:] = values.astype("float32")
    handle.flush()
    payload = buffer.getvalue()
    handle.close()
    return payload


def test_index_range_keeps_only_cell_centres_inside_the_box() -> None:
    # Dublin is narrower than one cell in latitude and exactly two in longitude.
    assert no2.index_range(DUBLIN) == (573, 573, 694, 695)
    assert no2.index_range(DELHI) == (472, 477, 1026, 1031)


def test_index_range_refuses_a_box_with_no_cell_centre() -> None:
    with pytest.raises(ValueError):
        no2.index_range((0.01, 0.01, 0.02, 0.02))


def test_parse_subset_weights_by_cosine_latitude() -> None:
    values = np.array([[1.0, 2.0], [5.0, 9.0]])
    payload = _payload(values)
    y0, y1 = 0, 1
    lat = np.array([-89.875, -89.625])
    weights = np.cos(np.deg2rad(lat))
    expected = float((weights[0] * 3 + weights[1] * 14) / (2 * weights.sum()))
    assert no2.parse_subset(payload, y0, y1, 0, 1) == pytest.approx(expected)
    assert not np.isclose(expected, 4.25)  # the unweighted mean is a different number


def test_parse_subset_ignores_fill_cells() -> None:
    values = np.array([[1.0, 1.0], [3.0, -1.2676506e30]])
    lat = np.array([-89.875, -89.625])
    weights = np.cos(np.deg2rad(lat))
    expected = float((weights[0] * 2 * 1 + weights[1] * 3) / (2 * weights[0] + weights[1]))
    assert no2.parse_subset(_payload(values), 0, 1, 0, 1) == pytest.approx(expected)


def test_an_all_fill_day_is_absent_not_zero() -> None:
    values = np.full((1, 2), -1.2676506e30)
    assert no2.parse_subset(_payload(values), 573, 573, 694, 695) is None


def test_a_subset_of_the_wrong_shape_is_rejected() -> None:
    values = np.zeros((3, 3))
    with pytest.raises(ValueError):
        no2.parse_subset(_payload(values), 0, 1, 0, 1)


def _series(tmp_path: Path) -> no2.DaySeries:
    series = no2.DaySeries(region_id="dublin_no2", box=DUBLIN, checkpoint_dir=tmp_path / ".pull")
    series.index = no2.index_range(DUBLIN)
    for day in range(1, 13):
        series.days[f"2005-01-{day:02d}"] = 1.0e15 + day * 1e13
    for day in range(1, 4):
        series.days[f"2005-02-{day:02d}"] = 2.0e15
    return series


def test_write_csv_round_trips_through_the_monthly_parser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(no2, "RAW", tmp_path)
    series = _series(tmp_path)
    monthly = omi.daily_to_monthly(no2.daily_frame(series))

    path = no2.write_csv(monthly, series, VARIABLES["no2"])

    assert read_giovanni_unit(path) == "molec/cm2"
    parsed = read_giovanni_csv(path)
    assert list(parsed.columns) == ["timestamp", "value"]
    assert parsed["timestamp"].tolist() == [pd.Timestamp("2005-01-01"), pd.Timestamp("2005-02-01")]
    assert parsed["value"].iloc[0] == pytest.approx(1.065e15)
    assert pd.isna(parsed["value"].iloc[1])  # three clear days is below the D22 minimum


def test_build_series_keeps_the_valid_day_counts(tmp_path: Path) -> None:
    series = _series(tmp_path)
    monthly = omi.daily_to_monthly(no2.daily_frame(series))
    csv_path = tmp_path / "no2_dublin_no2.csv"
    csv_path.write_text("Month,Mean\n2005-01,1e15\n", encoding="utf-8")

    parquet, provenance = no2.build_series(
        monthly, series, VARIABLES["no2"], csv_path, tmp_path / "processed"
    )

    frame = pd.read_parquet(parquet)
    assert len(frame) == 252  # 2005-01 .. 2025-12
    january = frame[frame["timestamp"] == pd.Timestamp("2005-01-01").date()].iloc[0]
    february = frame[frame["timestamp"] == pd.Timestamp("2005-02-01").date()].iloc[0]
    assert january["n_valid_days"] == 12
    assert january["value"] == pytest.approx(1.065e15)
    assert february["n_valid_days"] == 3
    assert pd.isna(february["value"])
    assert "below the 10-day minimum" in february["quality_summary"]
    assert frame["coverage_fraction"].isna().all()

    text = provenance.read_text(encoding="utf-8")
    assert "OPeNDAP" in text
    assert "-6.38,53.38,-6.12,53.38" in text


def test_pull_region_stores_values_not_tuples(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The checkpoint is `day -> value`; a future must not leak its tuple into it."""
    series = no2.DaySeries(region_id="dublin_no2", box=DUBLIN, checkpoint_dir=tmp_path / ".pull")
    granules = {
        "2005-01-01": "https://example.test/a",
        "2005-01-02": "https://example.test/b",
        "2005-01-03": "https://example.test/c",
    }
    monkeypatch.setattr(no2, "fetch_day", lambda *args, **kwargs: 1.5e15)

    no2.pull_region(series, granules, "token", workers=2, say=lambda *a, **k: None)

    assert series.days == {
        "2005-01-01": 1.5e15,
        "2005-01-02": 1.5e15,
        "2005-01-03": 1.5e15,
    }
    reloaded = no2.DaySeries(region_id="dublin_no2", box=DUBLIN, checkpoint_dir=tmp_path / ".pull")
    reloaded.load()
    assert reloaded.days == series.days


def test_a_checkpoint_with_non_numeric_values_is_refused(tmp_path: Path) -> None:
    series = no2.DaySeries(region_id="dublin_no2", box=DUBLIN, checkpoint_dir=tmp_path / ".pull")
    series.checkpoint_dir.mkdir(parents=True)
    series.checkpoint().write_text(
        '{"days": {"2005-01-01": ["2005-01-01", 1e15]}}', encoding="utf-8"
    )

    with pytest.raises(TypeError, match="not a number"):
        series.load()
