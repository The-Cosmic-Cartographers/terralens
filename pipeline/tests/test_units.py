"""Tests for the unit conversions (NAS-7)."""

from __future__ import annotations

import pandas as pd
import pytest

from pipeline.units import canonical_unit, convert


def _series(value: float, start: str = "2024-02-01") -> pd.Series:
    index = pd.DatetimeIndex([pd.Timestamp(start)])
    return pd.Series([value], index=index, dtype="float64")


def test_kelvin_to_celsius() -> None:
    result = convert(_series(273.15), "K", "°C")
    assert result.iloc[0] == pytest.approx(0.0)


def test_celsius_to_kelvin_round_trips() -> None:
    result = convert(_series(12.5), "degC", "K")
    assert result.iloc[0] == pytest.approx(285.65)


def test_evapotranspiration_to_mm_per_day() -> None:
    result = convert(_series(1.0 / 86_400.0), "kg/m2/s", "mm/day")
    assert result.iloc[0] == pytest.approx(1.0)


def test_mm_per_hour_to_mm_per_month_uses_the_real_month_length() -> None:
    february = convert(_series(1.0, "2024-02-01"), "mm/hr", "mm/month")
    assert february.iloc[0] == pytest.approx(29 * 24)
    january = convert(_series(1.0, "2024-01-01"), "mm/hr", "mm/month")
    assert january.iloc[0] == pytest.approx(31 * 24)


def test_mm_per_day_to_mm_per_month() -> None:
    result = convert(_series(2.0, "2023-02-01"), "mm/day", "mm/month")
    assert result.iloc[0] == pytest.approx(2.0 * 28)


def test_same_unit_is_a_passthrough() -> None:
    result = convert(_series(7.0), "kg m-2", "kg/m2")
    assert result.iloc[0] == pytest.approx(7.0)


def test_monthly_conversion_needs_a_datetime_index() -> None:
    with pytest.raises(ValueError):
        convert(pd.Series([1.0]), "mm/hr", "mm/month")


def test_unknown_pair_raises() -> None:
    with pytest.raises(ValueError, match="no conversion"):
        convert(_series(1.0), "kg/m2", "furlongs")


def test_canonical_unit_folds_spellings() -> None:
    assert canonical_unit("K") == canonical_unit("kelvin")
    assert canonical_unit("kg m-2 s-1") == canonical_unit("kg/m2/s")
