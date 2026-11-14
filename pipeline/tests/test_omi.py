"""Daily OMI -> monthly aggregation (D22, NAS-27)."""

from __future__ import annotations

import pandas as pd
import pytest

from pipeline.omi import MIN_VALID_DAYS, daily_to_monthly


def daily(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["timestamp", "value"])


def days_in(year: int, month: int, count: int, value: float = 1.0) -> list[tuple[str, float]]:
    return [(f"{year}-{month:02d}-{day:02d}", value) for day in range(1, count + 1)]


def test_a_month_is_the_mean_of_its_valid_days() -> None:
    rows = [(f"2020-01-{day:02d}", 10.0 + day) for day in range(1, 21)]

    out = daily_to_monthly(daily(rows))

    assert len(out) == 1
    assert out.loc[0, "valid_days"] == 20
    assert out.loc[0, "value"] == pytest.approx(sum(10.0 + day for day in range(1, 21)) / 20)
    assert out.loc[0, "timestamp"] == pd.Timestamp("2020-01-01")


def test_a_month_below_the_minimum_keeps_its_counts_and_loses_its_value() -> None:
    out = daily_to_monthly(daily(days_in(2020, 2, 9)))

    assert out.loc[0, "valid_days"] == 9
    assert pd.isna(out.loc[0, "value"])
    assert "below the" in out.loc[0, "quality_summary"]
    assert out.loc[0, "coverage_fraction"] == pytest.approx(9 / 29)


def test_exactly_the_minimum_passes() -> None:
    out = daily_to_monthly(daily(days_in(2020, 3, MIN_VALID_DAYS, value=7.0)))

    assert out.loc[0, "valid_days"] == MIN_VALID_DAYS
    assert out.loc[0, "value"] == pytest.approx(7.0)
    assert "below the" not in out.loc[0, "quality_summary"]


def test_a_month_with_no_retrieval_is_kept_as_a_null_row() -> None:
    rows = days_in(2020, 1, 12) + days_in(2020, 3, 12, value=2.0)

    out = daily_to_monthly(daily(rows))

    assert list(out["timestamp"]) == [
        pd.Timestamp("2020-01-01"),
        pd.Timestamp("2020-02-01"),
        pd.Timestamp("2020-03-01"),
    ]
    february = out.iloc[1]
    assert february["valid_days"] == 0
    assert february["coverage_fraction"] == 0.0
    assert pd.isna(february["value"])
    assert out.iloc[2]["value"] == pytest.approx(2.0)


def test_a_repeated_day_is_counted_once_and_the_last_value_wins() -> None:
    rows = days_in(2020, 1, 10) + [("2020-01-05", 50.0)]

    out = daily_to_monthly(daily(rows))

    assert out.loc[0, "valid_days"] == 10
    assert out.loc[0, "value"] == pytest.approx((1.0 * 9 + 50.0) / 10)


def test_leap_february_uses_29_days_in_the_denominator() -> None:
    out = daily_to_monthly(daily(days_in(2020, 2, 12)))

    assert out.loc[0, "days_in_month"] == 29
    assert out.loc[0, "coverage_fraction"] == pytest.approx(12 / 29)


def test_an_empty_frame_is_rejected() -> None:
    with pytest.raises(ValueError):
        daily_to_monthly(pd.DataFrame(columns=["timestamp", "value"]))
