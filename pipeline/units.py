"""Unit conversions for the Lineup pipeline.

Every conversion is explicit: an unknown pair raises instead of returning values
in the wrong unit, because a wrong unit is a wrong finding.
"""

from __future__ import annotations

import pandas as pd

_ALIASES: dict[str, str] = {
    "k": "kelvin",
    "kelvin": "kelvin",
    "c": "celsius",
    "degc": "celsius",
    "deg c": "celsius",
    "°c": "celsius",
    "celsius": "celsius",
    "kg/m2/s": "kg_m2_s",
    "kg/m^2/s": "kg_m2_s",
    "kg m-2 s-1": "kg_m2_s",
    "kg_m2_s": "kg_m2_s",
    "mm/hr": "mm_per_hour",
    "mm/h": "mm_per_hour",
    "mm hour-1": "mm_per_hour",
    "mm/day": "mm_per_day",
    "mm/d": "mm_per_day",
    "mm/day-1": "mm_per_day",
    "mm/month": "mm_per_month",
    "mm/mon": "mm_per_month",
    "kg/m2": "kg_m2",
    "kg m-2": "kg_m2",
    "mm": "mm",
    "molec/cm2": "molec_cm2",
}

SECONDS_PER_DAY = 86_400.0
HOURS_PER_DAY = 24.0


def canonical_unit(unit: str) -> str:
    """Map a unit spelling to one canonical name."""
    return _ALIASES.get(unit.strip().lower(), unit.strip().lower())


def _days_in_month(index: pd.Index) -> pd.Series:
    if not isinstance(index, pd.DatetimeIndex):
        raise ValueError("a monthly conversion needs a DatetimeIndex of month starts")
    return pd.Series(index.days_in_month, index=index, dtype="float64")


def convert(
    values: pd.Series,
    from_unit: str,
    to_unit: str,
    index: pd.Index | None = None,
) -> pd.Series:
    """Convert ``values`` from one unit to another, raising on an unknown pair.

    ``index`` supplies the month timestamps for conversions into an accumulation
    (mm/day -> mm/month, mm/hr -> mm/month).
    """
    source = canonical_unit(from_unit)
    target = canonical_unit(to_unit)
    numbers = values.astype("float64")

    if source == target:
        return numbers
    if (source, target) == ("kelvin", "celsius"):
        return numbers - 273.15
    if (source, target) == ("celsius", "kelvin"):
        return numbers + 273.15

    month_index = index if index is not None else values.index
    if (source, target) == ("kg_m2_s", "mm_per_day"):
        return numbers * SECONDS_PER_DAY
    if (source, target) == ("kg_m2_s", "mm_per_month"):
        return numbers * SECONDS_PER_DAY * _days_in_month(month_index)
    if (source, target) == ("mm_per_hour", "mm_per_month"):
        return numbers * HOURS_PER_DAY * _days_in_month(month_index)
    if (source, target) == ("mm_per_day", "mm_per_month"):
        return numbers * _days_in_month(month_index)
    if (source, target) == ("kg_m2", "mm"):
        # 1 kg m-2 of water is 1 mm of water.
        return numbers

    raise ValueError(f"no conversion from {from_unit!r} to {to_unit!r}")
