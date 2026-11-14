"""Tests for the Time Machine windows generator (NAS-29).

The claim that matters: the incremental S must equal a direct, from-scratch
seasonal Mann-Kendall on the same window, for every window.
"""

from __future__ import annotations

import json
import math
import time

import numpy as np
import pytest

from analysis import stats as tl
from analysis import windows as tw


def synthetic(years: int, seed: int = 7, trend: float = 0.03, noise: float = 1.5):
    rng = np.random.default_rng(seed)
    months = np.arange(years * 12)
    values = (
        12.0
        + 4.0 * np.sin(2 * math.pi * (months % 12) / 12)
        + trend * (months / 12.0)
        + rng.normal(0, noise, months.size)
    )
    matrix = values.reshape(years, 12)
    return matrix - matrix.mean(axis=0), np.arange(1981, 1981 + years)


@pytest.fixture(scope="module")
def built():
    anomalies, years = synthetic(45)
    return anomalies, years, tw.build_windows(anomalies, years, min_window_years=10)


def test_window_count_matches_the_closed_form(built):
    _, years, rows = built
    n = years.size
    assert len(rows) == (n - 10 + 1) * (n - 10 + 2) // 2


def test_incremental_matches_direct_recomputation(built):
    anomalies, years, rows = built
    rng = np.random.default_rng(11)
    for idx in rng.choice(len(rows), size=40, replace=False):
        row = rows[idx]
        direct = tw.verify_window(anomalies, years, row["start"], row["end"])
        assert row["p_value"] == pytest.approx(direct["p_value"], abs=1e-12)
        assert row["sen_slope_per_year"] == pytest.approx(direct["sen_slope_per_year"], abs=1e-12)
        assert row["_debug"]["S"] == pytest.approx(direct["S"], abs=1e-9)


def test_full_window_matches_the_headline_pipeline(built):
    anomalies, years, rows = built
    full = next(r for r in rows if r["start"] == years[0] and r["end"] == years[-1])

    # rebuild raw values (the headline applies its own climatology, so feed it
    # the un-anomalised series with a zero-baseline to compare like with like)
    values = anomalies + 12.0
    rows_in = [
        {
            "year": int(years[y]),
            "month": m + 1,
            "value": float(values[y, m]),
            "coverage_fraction": 1.0,
        }
        for y in range(years.size)
        for m in range(12)
    ]
    headline = tl.analyze_series(
        rows_in,
        dataset_id="t",
        variable_id="T2M",
        region_id="r",
        unit="degC",
        window=None,
        baseline=None,
        annual_agg="mean",
        with_pettitt=False,
        with_seasonal_strip=False,
    )
    assert full["p_value"] == pytest.approx(headline["p_value"], abs=1e-9)
    assert full["sen_slope_per_year"] == pytest.approx(headline["sen_slope_per_year"], abs=1e-9)


def test_confidence_intervals_are_ordered_and_narrow_with_length(built):
    _, _, rows = built
    for row in rows:
        low, high = row["confidence_interval_95"]
        assert low <= high

    def width(row):
        low, high = row["confidence_interval_95"]
        return high - low

    short = next(r for r in rows if r["n_years"] == 10)
    long = next(r for r in rows if r["n_years"] == 45)
    assert width(long) < width(short)


def test_incomplete_years_never_enter_a_window():
    anomalies, years = synthetic(45)
    gappy = anomalies.copy()
    gappy[3, 0] = np.nan
    gappy[20, 5] = np.nan
    rows = tw.build_windows(gappy, years, min_window_years=10)
    assert not [r for r in rows if r["start"] == years[3] or r["end"] == years[3]]


def test_bh_runs_within_a_window_and_sets_verdicts():
    family = [
        {
            "start": 1981,
            "end": 2025,
            "variable_id": "t2m",
            "p_value": 0.001,
            "sen_slope_per_year": 0.03,
            "confidence_interval_95": [0.02, 0.04],
            "verdict": None,
        },
        {
            "start": 1981,
            "end": 2025,
            "variable_id": "precipitation",
            "p_value": 0.02,
            "sen_slope_per_year": -0.5,
            "confidence_interval_95": [-0.9, -0.1],
            "verdict": None,
        },
        {
            "start": 1981,
            "end": 2025,
            "variable_id": "soil_moisture_0_10",
            "p_value": 0.30,
            "sen_slope_per_year": 0.0,
            "confidence_interval_95": [-0.1, 0.1],
            "verdict": None,
        },
        {
            "start": 1990,
            "end": 2025,
            "variable_id": "t2m",
            "p_value": 0.01,
            "sen_slope_per_year": 0.04,
            "confidence_interval_95": [0.01, 0.07],
            "verdict": None,
        },
    ]
    final = tw.finalize_window_family(family)
    first_window = [r for r in final if r["start"] == 1981]
    assert all(r["adjusted_p_value"] >= r["p_value"] - 1e-12 for r in first_window)
    assert all(r["verdict"] in tl.VERDICT_LABEL for r in final)
    # a second window must not be corrected against the first one
    assert len([r for r in final if r["start"] == 1990]) == 1


def test_contract_rows_drop_test_fields_and_round(built):
    _, _, rows = built
    contract = tw.contract_rows(rows)
    assert all(not any(key.startswith("_") for key in row) for row in contract)
    required = {
        "start",
        "end",
        "sen_slope_per_year",
        "confidence_interval_95",
        "p_value",
        "adjusted_p_value",
        "verdict",
    }
    assert all(required <= set(row) for row in contract)
    assert len(json.dumps(contract)) < len(json.dumps(rows))


def test_build_is_fast_enough_for_the_pipeline(built):
    anomalies, years, _ = built
    start = time.perf_counter()
    tw.build_windows(anomalies, years, min_window_years=10)
    assert time.perf_counter() - start < 2.0


def test_short_records_return_no_windows():
    anomalies, years = synthetic(8)
    assert tw.build_windows(anomalies, years, min_window_years=10) == []


def test_window_never_spans_a_year_dropped_for_missing_months():
    """NAS-59: a window must be the span it claims, not a subset of it."""
    anomalies, years = synthetic(45)
    gappy = anomalies.copy()
    gappy[20, 3] = np.nan  # one month missing in 2001
    gap = int(years[20])
    report: dict = {}

    rows = tw.build_windows(gappy, years, min_window_years=10, report=report)

    assert not [r for r in rows if r["start"] <= gap <= r["end"]]
    assert all(r["n_years"] == r["end"] - r["start"] + 1 for r in rows)
    assert report["years_dropped_incomplete"] == 1
    assert report["windows_skipped_for_missing_years"] > 0
    # the record on either side of the gap is still usable
    assert any(r["start"] < gap for r in rows)
    assert any(r["start"] > gap for r in rows)


def test_a_complete_record_reports_no_skips():
    anomalies, years = synthetic(45)
    report: dict = {}

    rows = tw.build_windows(anomalies, years, min_window_years=10, report=report)

    assert len(rows) == 666
    assert report == {"years_dropped_incomplete": 0, "windows_skipped_for_missing_years": 0}


def test_require_full_coverage_false_restores_the_old_behaviour():
    """The escape hatch exists for experiments; shipped results never use it."""
    anomalies, years = synthetic(45)
    gappy = anomalies.copy()
    gappy[20, 3] = np.nan
    gap = int(years[20])

    rows = tw.build_windows(gappy, years, min_window_years=10, require_full_coverage=False)

    spanning = [r for r in rows if r["start"] <= gap <= r["end"]]
    assert spanning
    assert all(r["n_years"] == r["end"] - r["start"] for r in spanning)
