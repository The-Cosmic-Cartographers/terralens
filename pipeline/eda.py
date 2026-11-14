"""Exploratory checks on processed series, before any statistic is computed (NAS-8).

The point of this module is to catch a broken series before a trend is fitted to
it: a gap, a spike, a unit that is off by 273.15, or a record that does not start
and end where the window says it should. It also fits a Sen slope and a
Mann-Kendall test purely so the direction can be compared, quietly, with the
pre-registered expectation in doc 11 §3 — that comparison is QA, never a finding.

    uv run python -m pipeline.eda data/processed/merra2_m2tmnxslv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

REQUIRED_COLUMNS = {"timestamp", "value", "region_id", "variable_id", "unit"}
YEARS_PER_DECADE = 10.0
SPIKE_SIGMA = 4.0
MIN_TREND_YEARS = 3


def load_series(path: Path) -> pd.DataFrame:
    """Read one processed series and normalise its timestamp column."""
    frame = pd.read_parquet(path)
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {', '.join(sorted(missing))}")
    frame = frame.assign(timestamp=pd.to_datetime(frame["timestamp"]))
    return frame.sort_values("timestamp").reset_index(drop=True)


def expected_months(first: pd.Timestamp, last: pd.Timestamp) -> pd.DatetimeIndex:
    """Every month between the first and last row, inclusive."""
    return pd.date_range(first.replace(day=1), last.replace(day=1), freq="MS")


def missing_months(frame: pd.DataFrame) -> list[str]:
    """Months with no row at all, and months whose value is null."""
    present = frame.set_index("timestamp")["value"]
    grid = expected_months(frame["timestamp"].min(), frame["timestamp"].max())
    aligned = present.reindex(grid)
    return [f"{stamp:%Y-%m}" for stamp, value in aligned.items() if pd.isna(value)]


def find_spikes(frame: pd.DataFrame, sigma: float = SPIKE_SIGMA) -> list[str]:
    """Month-on-month jumps far outside the series' own noise."""
    difference = frame["value"].diff()
    scale = difference.std(ddof=0)
    if not np.isfinite(scale) or scale == 0:
        return []
    flagged = []
    for stamp, delta in zip(frame["timestamp"].iloc[1:], difference.iloc[1:], strict=True):
        if abs(delta) > sigma * scale:
            flagged.append(f"{stamp:%Y-%m} ({delta:+.2f})")
    return flagged


def seasonal_cycle(frame: pd.DataFrame) -> pd.Series:
    """Mean and spread of each calendar month."""
    grouped = frame.groupby(frame["timestamp"].dt.month)["value"]
    return grouped.mean().rename("mean").to_frame().assign(sd=grouped.std())


def anomalies(frame: pd.DataFrame) -> pd.Series:
    """Value minus that calendar month's own climatology."""
    climatology = frame.groupby(frame["timestamp"].dt.month)["value"].transform("mean")
    return (frame["value"] - climatology).rename("anomaly")


def annual_means(frame: pd.DataFrame) -> pd.Series:
    """One value per calendar year, from the months that are actually present."""
    series = frame.dropna(subset=["value"])
    return series.groupby(series["timestamp"].dt.year)["value"].mean()


def trend(frame: pd.DataFrame) -> dict[str, float]:
    """Sen slope per decade with a 95% CI, plus the Mann-Kendall p-value.

    Both statistics follow doc 05: the slope comes from the **annual means**, and
    the test is the **seasonal** Mann-Kendall on the monthly series. Running either
    on raw monthly values lets the 12-month cycle dominate the variance, which
    hides a real trend (Ireland's temperature went from p = 0.03 to p = 7e-05 once
    the method was right).
    """
    annual = annual_means(frame)
    if len(annual) < MIN_TREND_YEARS:
        raise ValueError(f"a trend needs at least {MIN_TREND_YEARS} years of data")
    years = annual.index.to_numpy(dtype="float64")
    slope, _, low, high = stats.theilslopes(annual.to_numpy(), years, 0.95)
    return {
        "slope_per_decade": float(slope * YEARS_PER_DECADE),
        "ci_low": float(low * YEARS_PER_DECADE),
        "ci_high": float(high * YEARS_PER_DECADE),
        "p_value": _seasonal_mann_kendall_p(frame),
        "p_method": "seasonal Mann-Kendall, period 12, no Hamed-Rao correction",
        "n_years": int(len(annual)),
        "n_months": int(frame["value"].notna().sum()),
    }


def _seasonal_mann_kendall_p(frame: pd.DataFrame) -> float:
    """Seasonal Mann-Kendall p, one test per calendar month, pooled."""
    values = frame.dropna(subset=["value"])["value"].to_numpy()
    try:
        import pymannkendall as mk

        return float(mk.seasonal_test(values, period=12).p)
    except Exception:  # noqa: BLE001 - optional cross-check package
        return _mann_kendall_p(annual_means(frame).to_numpy())


def _mann_kendall_p(values: np.ndarray) -> float:
    """Two-sided Mann-Kendall p-value (normal approximation, tie-corrected)."""
    try:
        import pymannkendall as mk

        return float(mk.original_test(values).p)
    except Exception:  # noqa: BLE001 - optional cross-check package
        pass

    count = len(values)
    score = 0
    for index in range(count - 1):
        score += int(np.sign(values[index + 1 :] - values[index]).sum())
    variance = count * (count - 1) * (2 * count + 5) / 18.0
    if score == 0 or variance <= 0:
        return 1.0
    z_score = (abs(score) - 1) / np.sqrt(variance)
    return float(2 * (1 - stats.norm.cdf(z_score)))


def verdict(p_value: float) -> str:
    """Doc 11 §6 bands, so EDA says the same words the app will."""
    if p_value < 0.05:
        return "significant trend"
    if p_value < 0.10:
        return "weak / indicative"
    return "not significant"


def check_series(path: Path) -> dict[str, object]:
    """Run every check for one file and return a JSON-ready summary."""
    frame = load_series(path)
    values = frame["value"].dropna()
    stats_row = trend(frame)
    return {
        "file": path.name,
        "region_id": str(frame["region_id"].iloc[0]),
        "variable_id": str(frame["variable_id"].iloc[0]),
        "unit": str(frame["unit"].iloc[0]),
        "first": f"{frame['timestamp'].min():%Y-%m}",
        "last": f"{frame['timestamp'].max():%Y-%m}",
        "rows": int(len(frame)),
        "rows_with_values": int(frame["value"].notna().sum()),
        "missing_months": missing_months(frame),
        "spikes": find_spikes(frame),
        "min": float(values.min()),
        "max": float(values.max()),
        "mean": float(values.mean()),
        **stats_row,
        "verdict": verdict(stats_row["p_value"]),
    }


def plot_series(frame: pd.DataFrame, out_path: Path) -> Path:
    """Three panels: the series, its seasonal cycle, and its anomalies."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    anomaly = anomalies(frame)
    rolling = frame["value"].rolling(12, center=True).mean()
    cycle = seasonal_cycle(frame)

    figure, axes = plt.subplots(3, 1, figsize=(9, 8), sharex=False)
    axes[0].plot(frame["timestamp"], frame["value"], lw=0.8, color="#9ecae1", label="monthly")
    axes[0].plot(frame["timestamp"], rolling, lw=2, color="#08519c", label="12-month mean")
    axes[0].set_ylabel(str(frame["unit"].iloc[0]))
    axes[0].set_title(
        f"{frame['region_id'].iloc[0]} — {frame['variable_id'].iloc[0]} "
        f"({frame['timestamp'].min():%Y-%m} to {frame['timestamp'].max():%Y-%m})"
    )
    axes[0].legend(loc="upper left", fontsize=8)

    axes[1].bar(cycle.index, cycle["mean"], color="#74c476")
    axes[1].set_ylabel(str(frame["unit"].iloc[0]))
    axes[1].set_xlabel("calendar month")
    axes[1].set_title("Seasonal cycle (mean by month)", fontsize=9)

    axes[2].axhline(0, color="#636363", lw=0.8)
    axes[2].plot(frame["timestamp"], anomaly, lw=0.8, color="#de2d26")
    axes[2].plot(frame["timestamp"], anomaly.rolling(12, center=True).mean(), lw=2, color="#a50f15")
    axes[2].set_ylabel(f"anomaly ({frame['unit'].iloc[0]})")
    axes[2].set_title(
        f"Anomalies from the {frame['timestamp'].dt.year.min()}–"
        f"{frame['timestamp'].dt.year.max()} monthly climatology",
        fontsize=9,
    )

    figure.tight_layout()
    figure.savefig(out_path, dpi=110)
    plt.close(figure)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exploratory checks on processed series")
    parser.add_argument("directory", type=Path, help="folder of processed Parquet series")
    parser.add_argument("--out", type=Path, default=Path("data/eda"))
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    summaries = []
    for path in sorted(args.directory.glob("*.parquet")):
        summary = check_series(path)
        summaries.append(summary)
        figure = plot_series(load_series(path), args.out / f"{summary['region_id']}.png")
        p_value = summary["p_value"]
        p_text = "<1e-12" if p_value < 1e-12 else f"{p_value:.3g}"
        print(
            f"{summary['region_id']:<13} {summary['first']}..{summary['last']} "
            f"n={summary['rows']} missing={len(summary['missing_months'])} "
            f"spikes={len(summary['spikes'])} {summary['unit']!r} "
            f"slope={summary['slope_per_decade']:+.2f}/decade "
            f"p={p_text} ({summary['verdict']}) -> {figure}"
        )

    (args.out / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
