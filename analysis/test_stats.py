"""Known-answer tests for analysis/stats.py (NAS-10, NAS-11).

Every case has an answer we can state before running the code, so a failure
means the implementation is wrong rather than the expectation being unclear.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from analysis import stats as tl


def monthly_rows(matrix: np.ndarray, start_year: int = 1981) -> list[dict]:
    rows = []
    for yi in range(matrix.shape[0]):
        for mi in range(12):
            value = matrix[yi, mi]
            if np.isnan(value):
                continue
            rows.append(
                {
                    "year": start_year + yi,
                    "month": mi + 1,
                    "value": float(value),
                    "coverage_fraction": 1.0,
                }
            )
    return rows


def analyze(matrix, *, start_year=1981, unit="mm", annual_agg="sum"):
    return tl.analyze_series(
        monthly_rows(matrix, start_year),
        dataset_id="test_dataset",
        variable_id="precip",
        region_id="test_region",
        unit=unit,
        annual_agg=annual_agg,
        window=None,
        baseline=None,
    )


def seasonal_series(years: int, trend_per_month: float, seed: int, noise: float = 8.0):
    rng = np.random.default_rng(seed)
    months = np.arange(years * 12)
    series = (
        200.0
        + 80.0 * np.sin(2 * math.pi * (months % 12) / 12)
        + trend_per_month * months
        + rng.normal(0, noise, months.size)
    )
    return series.reshape(years, 12)


def test_perfect_line_slope_is_exact():
    t = np.arange(45)
    line = 100.0 + 2.0 * t
    assert tl.sen_slope(line, t) == pytest.approx(2.0)
    s, var, _ = tl.mk_statistic(line)
    p, _ = tl.mk_pvalue(s, var)
    assert p < 1e-6


def test_noise_false_positive_rate_is_near_nominal():
    rng = np.random.default_rng(42)
    hits = 0
    for _ in range(200):
        noise = rng.normal(0, 1, 45)
        s, var, _ = tl.mk_statistic(noise)
        p, _ = tl.mk_pvalue(s, var)
        hits += p < 0.05
    assert 0.01 <= hits / 200 <= 0.10


def test_flat_series_has_no_trend():
    flat = np.full(30, 7.0)
    s, var, _ = tl.mk_statistic(flat)
    p, _ = tl.mk_pvalue(s, var)
    assert s == 0
    assert p == 1.0


def test_seasonal_mk_finds_seasonal_trend_and_matches_pymannkendall():
    matrix = seasonal_series(30, trend_per_month=0.08, seed=3)
    result = tl.seasonal_mk(matrix)
    assert result["p_value"] < 0.01

    pymk = pytest.importorskip("pymannkendall")
    theirs = pymk.seasonal_test(matrix.ravel().tolist(), period=12)
    assert result["p_value"] == pytest.approx(theirs.p, abs=0.02)


def test_anomaly_route_keeps_the_trend():
    matrix = seasonal_series(30, trend_per_month=0.08, seed=3)
    anomalies = matrix - np.nanmean(matrix, axis=0)
    assert tl.seasonal_mk(anomalies)["p_value"] < 0.01


def test_heavy_gaps_are_withheld_without_statistics():
    matrix = seasonal_series(30, trend_per_month=0.08, seed=4)
    matrix[:, 0:4] = np.nan  # 33 % of months missing
    row = analyze(matrix)
    assert row["verdict"] == "not_enough_data"
    assert row["p_value"] is None
    assert row["sen_slope_per_year"] is None
    assert "missing" in row["withheld_reason"]


def test_short_record_is_withheld():
    matrix = seasonal_series(30, trend_per_month=0.08, seed=4)[:8]
    row = analyze(matrix, start_year=2018)
    assert row["verdict"] == "not_enough_data"
    assert "complete years" in row["withheld_reason"]


def test_pettitt_finds_a_clean_step():
    rng = np.random.default_rng(5)
    step = np.concatenate([rng.normal(300, 25, 20), rng.normal(500, 25, 20)])
    result = tl.pettitt_test(step, np.arange(1981, 1981 + step.size))
    assert result is not None
    assert abs(result["change_point_year"] - 2000) <= 2
    assert result["p_value"] < 0.01


def test_pettitt_does_not_fire_on_noise():
    rng = np.random.default_rng(6)
    hits = 0
    for _ in range(100):
        result = tl.pettitt_test(rng.normal(0, 1, 40), np.arange(1981, 2021))
        hits += bool(result and result["p_value"] < 0.05)
    assert hits / 100 <= 0.15


def test_benjamini_hochberg_rejects_the_expected_set():
    rejected = tl.benjamini_hochberg([0.001, 0.01, 0.04, 0.20], alpha=0.05)
    assert list(rejected) == [True, True, False, False]


def test_detectability_is_in_a_sane_range():
    rng = np.random.default_rng(7)
    years = tl.detectability_years(rng.normal(0, 90, 45 * 12), 0.8)
    assert years is not None
    assert 20 < years < 120


def test_sparkline_caps_and_tracks_the_series():
    spark = tl.sparkline(np.arange(45, dtype=float))
    assert len(spark) == 24  # bucket means, so the last point is 43.5 not 44
    assert spark[0] == pytest.approx(0.0)
    assert spark[-1] == pytest.approx(43.5)
    assert tl.sparkline([1.0, 2.0, 3.0]) == [1.0, 2.0, 3.0]
    assert tl.sparkline([]) == []
    assert tl.sparkline([np.nan, np.nan]) == []


def test_seasonal_strip_localises_a_winter_trend():
    years = 40
    idx = np.arange(years * 12)
    month_numbers = (idx % 12) + 1
    winter = np.where(np.isin(month_numbers, [12, 1, 2]), 2.0 * (idx / 12.0), 0.0)
    series = 150.0 + 40.0 * np.sin(2 * math.pi * (idx % 12) / 12) + winter
    matrix = series.reshape(years, 12)
    slopes = tl.seasonal_slopes(matrix, np.arange(1981, 1981 + years))
    assert abs(slopes["DJF"]) > 0.5
    assert abs(slopes["MAM"]) < 0.2


def test_end_to_end_recovers_an_injected_trend():
    rng = np.random.default_rng(8)
    years = 45
    months = np.arange(years * 12)
    temp = (
        10.0
        + 3.0 * np.sin(2 * math.pi * (months % 12) / 12)
        + 0.04 * (months / 12.0)
        + rng.normal(0, 0.6, months.size)
    )
    row = analyze(temp.reshape(years, 12), unit="degC", annual_agg="mean")
    assert row["verdict"] == "significant"
    assert row["sen_slope_per_year"] == pytest.approx(0.04, abs=0.015)
    low, high = row["confidence_interval_95"]
    assert low <= row["sen_slope_per_year"] <= high
    # contract: detectability is only filled for non-significant verdicts
    assert row["detect_years"] is None


def test_verdict_is_set_from_the_computed_p_value():
    # Regression: a fully computed row once still reported "not enough data".
    matrix = seasonal_series(40, trend_per_month=0.1, seed=9)
    row = analyze(matrix)
    assert row["verdict"] != "not_enough_data"
    assert row["adjusted_p_value"] is not None
    assert row["adjusted_p_value"] == pytest.approx(row["p_value"])


def test_detectability_is_suppressed_when_the_record_is_long_enough():
    # 76 years of skewed rainfall: n* comes out shorter than the record, so the
    # number would contradict the row and must be withheld with a caveat.
    rng = np.random.default_rng(10)
    matrix = rng.gamma(shape=2.0, scale=40.0, size=(76, 12))
    row = analyze(matrix, start_year=1950)
    if row["verdict"] != "significant" and row["adjusted_p_value"] is not None:
        assert row["detect_years"] is None
        assert "record_long_enough_but_not_significant" in row["caveats"]


def test_analyze_series_reports_diagnostics_by_default():
    matrix = seasonal_series(35, trend_per_month=0.05, seed=11)
    row = analyze(matrix)
    assert row["change_point"] is not None
    assert set(row["seasonal_slopes"]) == {"DJF", "MAM", "JJA", "SON"}
