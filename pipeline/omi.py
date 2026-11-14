"""Daily OMI NO2 -> monthly series with valid-day counts (D22, NAS-27).

OMI (OMNO2d) is a *daily* product: one value per day per box, with cloud-screened
retrievals simply absent. Two things therefore differ from the monthly products:

* the monthly value is the mean of the daily values that exist, not a supplied
  monthly mean, and it has to be reproducible from the daily file;
* a month with only a handful of clear days is not comparable with a month of
  thirty. D22 sets the rule: a monthly OMI value needs **at least 10 valid days**;
  below that the month is kept as a null row with its day count recorded.

Where the count goes matters. Doc 04 §1 has `n_valid_days` for exactly this
(`SeriesRow.n_valid_days`, "daily products only"), so the count is written there.
It must **not** be turned into `coverage_fraction`: the analysis treats a coverage
fraction below 0.5 as a missing month, so a 14-of-31 day month that passed the
10-day rule would be silently dropped one layer later. For a Giovanni area
average there are no per-cell counts, so `coverage_fraction` stays null.
"""

from __future__ import annotations

import calendar

import pandas as pd

MIN_VALID_DAYS = 10


def daily_to_monthly(
    daily: pd.DataFrame,
    *,
    min_valid_days: int = MIN_VALID_DAYS,
) -> pd.DataFrame:
    """Aggregate `{timestamp, value}` daily rows into calendar months.

    Returns one row per month from the first to the last month covered, with
    columns `timestamp` (month start), `value`, `n_valid_days` and
    `quality_summary`.

    Months with fewer than `min_valid_days` valid days keep a null `value` but
    keep their count, so a thin month is visible rather than silently averaged.
    `coverage_fraction` is deliberately not produced here; see the module note.
    """
    if min_valid_days < 1:
        raise ValueError("min_valid_days must be at least 1")
    if daily.empty:
        raise ValueError("the daily frame is empty")

    frame = daily[["timestamp", "value"]].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"]).dt.normalize()
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.drop_duplicates("timestamp", keep="last")

    month = frame["timestamp"].dt.to_period("M").dt.to_timestamp()
    grouped = frame.groupby(month)["value"]
    monthly = pd.DataFrame({"n_valid_days": grouped.count(), "value": grouped.mean()})

    # A day with no retrieval is absent from the file, not a row with NaN, so
    # months can be missing entirely. Keep them: the statistics layer decides
    # what a missing month means, and a silent hole would shorten the record.
    index = pd.date_range(monthly.index.min(), monthly.index.max(), freq="MS")
    monthly = monthly.reindex(index)
    monthly["n_valid_days"] = monthly["n_valid_days"].fillna(0).astype("int64")

    days_in_month = [calendar.monthrange(stamp.year, stamp.month)[1] for stamp in monthly.index]
    thin = monthly["n_valid_days"] < min_valid_days
    monthly.loc[thin, "value"] = float("nan")
    monthly["quality_summary"] = [
        f"{int(days)} of {total} days with a valid retrieval"
        + ("" if days >= min_valid_days else f"; below the {min_valid_days}-day minimum")
        for days, total in zip(monthly["n_valid_days"], days_in_month, strict=True)
    ]

    monthly = monthly.reset_index().rename(columns={"index": "timestamp"})
    monthly["timestamp"] = monthly["timestamp"].dt.normalize()
    return monthly[["timestamp", "value", "n_valid_days", "quality_summary"]]
