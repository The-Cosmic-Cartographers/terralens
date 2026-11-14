"""Tests for the exploratory checks (NAS-8)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline.eda import (
    anomalies,
    check_series,
    expected_months,
    find_spikes,
    missing_months,
    seasonal_cycle,
    trend,
    verdict,
)


def _frame(
    start: str = "1981-01-01",
    years: int = 10,
    slope_per_year: float = 0.0,
    jitter: float = 0.0,
) -> pd.DataFrame:
    index = pd.date_range(start, periods=years * 12, freq="MS")
    months = np.arange(len(index))
    values = 10.0 + slope_per_year * months / 12.0 + 3.0 * np.sin(2 * np.pi * (months % 12) / 12)
    if jitter:
        # A perfectly repeating sine leaves Theil-Sen with a degenerate interval;
        # real series never do, so the fixture should not either.
        values = values + np.random.default_rng(0).normal(0.0, jitter, len(index))
    return pd.DataFrame(
        {
            "timestamp": index,
            "value": values,
            "region_id": "ireland",
            "variable_id": "t2m",
            "unit": "°C",
        }
    )


def test_expected_months_covers_both_ends() -> None:
    grid = expected_months(pd.Timestamp("2000-03-01"), pd.Timestamp("2001-02-01"))
    assert len(grid) == 12
    assert grid[0] == pd.Timestamp("2000-03-01")
    assert grid[-1] == pd.Timestamp("2001-02-01")


def test_missing_months_finds_a_deleted_row_and_a_null() -> None:
    frame = _frame(years=2)
    dropped = frame["timestamp"].iloc[5].strftime("%Y-%m")
    frame = frame.drop(index=5).reset_index(drop=True)
    nulled = frame["timestamp"].iloc[2].strftime("%Y-%m")
    frame.loc[frame.index[2], "value"] = np.nan

    missing = missing_months(frame)

    assert sorted(missing) == sorted([dropped, nulled])


def test_find_spikes_flags_a_single_jump_only() -> None:
    frame = _frame(years=5)
    frame.loc[30, "value"] += 40.0
    spikes = find_spikes(frame)
    assert len(spikes) == 2, "the jump in and the jump back out"
    assert spikes[0].startswith(frame["timestamp"].iloc[30].strftime("%Y-%m"))


def test_seasonal_cycle_has_twelve_months() -> None:
    cycle = seasonal_cycle(_frame(years=3))
    assert list(cycle.index) == list(range(1, 13))
    assert cycle["mean"].idxmax() == 4, "this sine peaks at index 3, i.e. April"


def test_anomalies_remove_the_monthly_mean() -> None:
    frame = _frame(years=4)
    frame["anomaly"] = anomalies(frame)
    by_month = frame.groupby(frame["timestamp"].dt.month)["anomaly"].mean()
    assert np.allclose(by_month.to_numpy(), 0.0, atol=1e-9)


def test_trend_recovers_a_known_slope() -> None:
    result = trend(_frame(years=30, slope_per_year=0.5, jitter=0.4))

    assert result["slope_per_decade"] == pytest.approx(5.0, abs=0.3)
    assert result["ci_low"] < result["slope_per_decade"] < result["ci_high"]
    assert result["ci_low"] < 5.0 < result["ci_high"], "the interval must cover the true slope"
    assert result["p_value"] < 0.01


def test_trend_rejects_a_series_shorter_than_three_years() -> None:
    with pytest.raises(ValueError):
        trend(_frame(years=2))


def test_verdict_bands_match_doc_11() -> None:
    assert verdict(0.01) == "significant trend"
    assert verdict(0.07) == "weak / indicative"
    assert verdict(0.4) == "not significant"


def test_check_series_summarises_a_file(tmp_path: Path) -> None:
    frame = _frame(years=5, slope_per_year=0.2)
    path = tmp_path / "ireland.parquet"
    frame.to_parquet(path, index=False)

    summary = check_series(path)

    assert summary["region_id"] == "ireland"
    assert summary["first"] == "1981-01"
    assert summary["rows"] == 60
    assert summary["missing_months"] == []
    assert summary["unit"] == "°C"
    assert summary["slope_per_decade"] > 0
