"""
TerraLens analysis — v0
=======================
Implements the statistics fixed in the Linear decision log (D6, D7, D21–D23) and
described in `05 · Scientific Method & Validation`.

Headline pipeline per variable x region
---------------------------------------
1. filter to the D21 window, reject months below the coverage gate       (D6)
2. withhold the row if < 10 complete years or > 20 % months missing      (D6)
3. monthly anomalies against the 1991–2020 baseline (full record if shorter)
4. seasonal Mann–Kendall on the monthly anomalies                       (D22)
5. Hamed–Rao variance correction from lag-1 autocorrelation              (D7)
6. Sen's slope per year (+ 95 % CI), reported per decade
7. Mann–Kendall on annual means as a sensitivity check                  (D22)
8. Benjamini–Hochberg across a lineup / compare family                  (D23)
9. verdict, effect size, detectability (Weatherhead 1998)              (D6, NAS-46)

Diagnostics emitted on every row (adopted 14 Nov, Nandini; diagnostics, not
verdict-makers, and deliberately NOT part of the BH family):
  * `pettitt_test`   — single change point; only meaningful when the record has
                       a level shift (Sahel-style flips)
  * `seasonal_slopes` — which season drives the trend (descriptive, no p-values)

Contract shape: the dict returned by `analyze_series` uses the field names from
`04 · Data & API Contracts`, schema 2 (trends.json).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence

import numpy as np
from scipy import stats as sps

# --- decided thresholds (D6 / D23) -----------------------------------------
ALPHA_SIGNIFICANT = 0.05
ALPHA_WEAK = 0.10
MIN_COMPLETE_YEARS = 10
MAX_MISSING_FRACTION = 0.20
MIN_MONTH_COVERAGE = 0.5
MIN_VALID_DAYS_OMI = 10

Z_95 = 1.959963984540054
MONTHS = tuple(range(1, 13))
SEASONS = {
    "DJF": (12, 1, 2),
    "MAM": (3, 4, 5),
    "JJA": (6, 7, 8),
    "SON": (9, 10, 11),
}


# ---------------------------------------------------------------------------
# Basic Mann–Kendall machinery
# ---------------------------------------------------------------------------
def mk_statistic(x: Sequence[float]) -> tuple[float, float, int]:
    """Mann–Kendall S and its tie-corrected variance for one series.

    S = sum_{i<j} sign(x_j - x_i); Var(S) = [n(n-1)(2n+5) - sum t(t-1)(2t+5)]/18
    NaNs are dropped. Returns (S, Var(S), n).
    """
    arr = np.asarray(x, dtype=float)
    arr = arr[~np.isnan(arr)]
    n = arr.size
    if n < 3:
        return 0.0, 0.0, n

    # vectorised pairwise sign sum
    later = arr[None, :]
    earlier = arr[:, None]
    s = float(np.sign(later - earlier)[np.triu_indices(n, k=1)].sum())

    _, counts = np.unique(arr, return_counts=True)
    ties = counts[counts > 1].astype(float)
    var_s = (n * (n - 1) * (2 * n + 5) - float(np.sum(ties * (ties - 1) * (2 * ties + 5)))) / 18.0
    return s, var_s, n


def mk_pvalue(s: float, var_s: float) -> tuple[float, float]:
    """Two-sided p and z for a Mann–Kendall S (continuity corrected)."""
    if var_s <= 0:
        return 1.0, 0.0
    if s > 0:
        z = (s - 1.0) / math.sqrt(var_s)
    elif s < 0:
        z = (s + 1.0) / math.sqrt(var_s)
    else:
        z = 0.0
    p = 2.0 * (1.0 - sps.norm.cdf(abs(z)))
    return float(min(max(p, 0.0), 1.0)), float(z)


def seasonal_mk(monthly: np.ndarray) -> dict:
    """Seasonal Mann–Kendall: per-month S summed, per-month variances summed.

    `monthly` is (years, 12); NaN marks a missing month. This matches the
    standard `pymannkendall.seasonal_test` construction, which is what the
    validation suite cross-checks against.
    """
    monthly = np.asarray(monthly, dtype=float)
    if monthly.ndim != 2:
        raise ValueError("monthly must be a 2-D (years, 12) array")

    s_total = 0.0
    var_total = 0.0
    per_season = []
    for m in range(monthly.shape[1]):
        column = monthly[:, m]
        s, var_s, n = mk_statistic(column)
        per_season.append({"month": m + 1, "n": n, "S": s, "var_S": var_s})
        s_total += s
        var_total += var_s

    p, z = mk_pvalue(s_total, var_total)
    return {
        "S": s_total,
        "var_S": var_total,
        "z": z,
        "p_value": p,
        "per_season": per_season,
        "years_used": int(np.sum(~np.isnan(monthly).all(axis=1))),
    }


def lag1_autocorrelation(series: Sequence[float]) -> float:
    """Lag-1 autocorrelation of a 1-D series, NaNs dropped, clipped to ±0.99."""
    arr = np.asarray(series, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size < 3:
        return 0.0
    rho = float(np.corrcoef(arr[:-1], arr[1:])[0, 1])
    if not np.isfinite(rho):
        return 0.0
    return float(np.clip(rho, -0.99, 0.99))


def hamed_rao_factor(series: Sequence[float]) -> float:
    """Variance-inflation factor n/n* for lag-1 autocorrelation (D7).

    AR(1) approximation: n/n* ≈ (1 + ρ) / (1 − ρ). The factor is never allowed
    below 1.0 — a negative ρ must not make the test optimistic.
    """
    rho = lag1_autocorrelation(series)
    factor = (1.0 + rho) / (1.0 - rho)
    return float(max(1.0, factor))


# ---------------------------------------------------------------------------
# Sen's slope and its confidence interval
# ---------------------------------------------------------------------------
def sen_slope(x: Sequence[float], t: Sequence[float] | None = None) -> float:
    """Median of all pairwise slopes; returns the slope in x-units per t-unit."""
    arr = np.asarray(x, dtype=float)
    if t is None:
        t_arr = np.arange(arr.size, dtype=float)
    else:
        t_arr = np.asarray(t, dtype=float)
    if arr.size != t_arr.size:
        raise ValueError("x and t must have the same length")

    ok = ~np.isnan(arr)
    arr, t_arr = arr[ok], t_arr[ok]
    n = arr.size
    if n < 3:
        return float("nan")

    i, j = np.triu_indices(n, k=1)
    slopes = (arr[j] - arr[i]) / (t_arr[j] - t_arr[i])
    slopes = slopes[np.isfinite(slopes)]
    if slopes.size == 0:
        return float("nan")
    return float(np.median(slopes))


def sen_ci(
    x: Sequence[float],
    t: Sequence[float] | None = None,
    var_s: float | None = None,
    alpha: float = ALPHA_SIGNIFICANT,
) -> tuple[float, float]:
    """Rank-based 95 % CI for Sen's slope (Gilbert 1987).

    Falls back to a percentile bootstrap when the rank indices are unusable
    (very short or heavily tied series).
    """
    arr = np.asarray(x, dtype=float)
    t_arr = np.arange(arr.size, dtype=float) if t is None else np.asarray(t, dtype=float)
    ok = ~np.isnan(arr)
    arr, t_arr = arr[ok], t_arr[ok]
    n = arr.size
    if n < 3:
        return (float("nan"), float("nan"))

    i, j = np.triu_indices(n, k=1)
    slopes = np.sort((arr[j] - arr[i]) / (t_arr[j] - t_arr[i]))
    slopes = slopes[np.isfinite(slopes)]
    big_n = slopes.size
    if big_n < 10:
        return (float("nan"), float("nan"))

    if var_s and var_s > 0:
        c = sps.norm.ppf(1 - alpha / 2.0) * math.sqrt(var_s)
        lo_idx = int(math.floor((big_n - c) / 2.0))
        hi_idx = int(math.ceil((big_n + c) / 2.0))
        if 0 <= lo_idx < hi_idx < big_n:
            return float(slopes[lo_idx]), float(slopes[hi_idx])

    # conservative fallback
    return float(np.percentile(slopes, 2.5)), float(np.percentile(slopes, 97.5))


# ---------------------------------------------------------------------------
# Detectability (Weatherhead et al. 1998)
# ---------------------------------------------------------------------------
def detectability_years(
    monthly_anomalies: Sequence[float], slope_per_year: float
) -> float | None:
    """Years of record needed to detect `slope_per_year` at 90 % power, 5 % level.

    n* ≈ [ (3.3 σ_N / |ω|) · sqrt((1 + φ)/(1 − φ)) ]^(2/3)
    σ_N = s.d. of MONTHLY anomalies, ω = slope per YEAR, φ = lag-1 autocorr.
    Returns None when it cannot be computed (no slope, too few points).
    """
    arr = np.asarray(monthly_anomalies, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size < 12 or not np.isfinite(slope_per_year) or slope_per_year == 0:
        return None
    sigma = float(np.std(arr, ddof=1))
    if sigma == 0:
        return None
    phi = lag1_autocorrelation(arr)
    core = (3.3 * sigma / abs(slope_per_year)) * math.sqrt((1.0 + phi) / (1.0 - phi))
    if not np.isfinite(core) or core <= 0:
        return None
    return float(core ** (2.0 / 3.0))


def sparkline(
    values: Sequence[float], years: Sequence[int] | None = None, points: int = 24
) -> list[float]:
    """Evenly spaced annual values for a Lineup row sparkline (schema 2a).

    Values are bucketed by position (not by calendar decade) so a row with gaps
    still produces a readable shape. NaNs are dropped before bucketing, so the
    caller must not treat the output as a time axis.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return []
    if arr.size <= points:
        return [float(v) for v in arr]

    edges = np.linspace(0, arr.size, points + 1, dtype=int)
    return [float(np.mean(arr[edges[k] : edges[k + 1]])) for k in range(points)]


def effect_size_swings(slope_per_year: float, n_years: int, annual_sd: float) -> float | None:
    """Change over the window expressed in units of the normal annual swing."""
    if not np.isfinite(slope_per_year) or annual_sd == 0 or not np.isfinite(annual_sd):
        return None
    return float(abs(slope_per_year * n_years) / annual_sd)


# ---------------------------------------------------------------------------
# Multiple comparisons and verdicts (D23 / D6)
# ---------------------------------------------------------------------------
def benjamini_hochberg(pvals: Iterable[float], alpha: float = ALPHA_SIGNIFICANT) -> np.ndarray:
    """Standard BH step-up; returns a boolean array of rejections."""
    p = np.asarray(list(pvals), dtype=float)
    n = p.size
    if n == 0:
        return np.zeros(0, dtype=bool)
    order = np.argsort(p)
    ranked = p[order]
    thresholds = (np.arange(1, n + 1) / n) * alpha
    below = ranked <= thresholds
    out = np.zeros(n, dtype=bool)
    if not below.any():
        return out
    k = int(np.where(below)[0].max())
    out[order[: k + 1]] = True
    return out


def verdict_from_p(adjusted_p: float | None, withheld: bool) -> str:
    """Map an adjusted p to the UI label (D23)."""
    if withheld or adjusted_p is None:
        return "not_enough_data"
    if adjusted_p < ALPHA_SIGNIFICANT:
        return "significant"
    if adjusted_p < ALPHA_WEAK:
        return "weak_evidence"
    return "no_clear_trend"


VERDICT_LABEL = {
    "significant": "Significant trend",
    "weak_evidence": "Weak evidence",
    "no_clear_trend": "No clear trend",
    "not_enough_data": "Not enough data",
}


# ---------------------------------------------------------------------------
# Optional diagnostics (not decided — off by default)
# ---------------------------------------------------------------------------
def pettitt_test(values: Sequence[float], years: Sequence[int]) -> dict | None:
    """Pettitt change-point test for a single level shift.

    U(t) = sum_{i<=t} sum_{j>t} sign(x_i - x_j)  (Mann–Whitney form)
    K = max |U(t)|;  p ≈ 2 exp(-6K²/(n³+n²)).
    Returns the most likely change year and the before/after means.

    Note: the asymptotic p is conservative for short records (roughly n < 50),
    so this errs towards missing a step rather than inventing one. That is the
    right failure mode for a diagnostic shown next to a headline verdict.
    """
    x = np.asarray(values, dtype=float)
    yrs = np.asarray(years, dtype=float)
    ok = ~np.isnan(x)
    x, yrs = x[ok], yrs[ok]
    n = x.size
    if n < 8:
        return None

    ranks = sps.rankdata(x)
    cumulative = np.cumsum(ranks)
    t = np.arange(1, n)  # split after index t-1
    u = 2.0 * cumulative[t - 1] - t * (n + 1.0)
    abs_u = np.abs(u)
    k = float(abs_u.max())
    idx = int(abs_u.argmax())
    p = 2.0 * math.exp(-6.0 * k**2 / (n**3 + n**2))
    p = float(min(max(p, 0.0), 1.0))

    split = idx + 1
    return {
        "change_point_year": int(yrs[split - 1]),
        "K": k,
        "p_value": p,
        "mean_before": float(np.nanmean(x[:split])),
        "mean_after": float(np.nanmean(x[split:])),
        "n": n,
    }


def seasonal_slopes(monthly: np.ndarray, years: Sequence[int]) -> dict:
    """Per-season Sen slopes (descriptive only — no p-values)."""
    monthly = np.asarray(monthly, dtype=float)
    yrs = np.asarray(years, dtype=float)
    out: dict[str, float | None] = {}
    for name, months in SEASONS.items():
        idx = [m - 1 for m in months]
        season_mean = np.nanmean(monthly[:, idx], axis=1)
        out[name] = sen_slope(season_mean, yrs)
    return out


# ---------------------------------------------------------------------------
# Row assembly
# ---------------------------------------------------------------------------
def _build_matrix(
    rows: Iterable[Mapping[str, float]], window: tuple[int, int] | None
) -> tuple[np.ndarray, np.ndarray, int]:
    """Assemble a (years, 12) value matrix from {year, month, value, coverage}."""
    start, end = window if window else (0, 9999)
    by_year: dict[int, dict[int, float]] = {}
    missing_below_coverage = 0
    for row in rows:
        year = int(row["year"])
        month = int(row["month"])
        if not (start <= year <= end):
            continue
        value = row.get("value")
        coverage = row.get("coverage_fraction", 1.0)
        if coverage is None:
            coverage = 1.0
        if value is None or not np.isfinite(value) or coverage < MIN_MONTH_COVERAGE:
            by_year.setdefault(year, {})[month] = np.nan
            missing_below_coverage += 1
        else:
            by_year.setdefault(year, {})[month] = float(value)

    if not by_year:
        return np.zeros((0, 12)), np.zeros(0), 0

    years = np.array(sorted(by_year), dtype=int)
    matrix = np.full((years.size, 12), np.nan, dtype=float)
    for row_idx, year in enumerate(years):
        for month, value in by_year[year].items():
            if 1 <= month <= 12:
                matrix[row_idx, month - 1] = value
    return matrix, years, missing_below_coverage


def _annual_series(matrix: np.ndarray, agg: str) -> np.ndarray:
    """Annual aggregate; NaN unless all 12 months are present."""
    complete = ~np.isnan(matrix).any(axis=1)
    if agg == "sum":
        annual = np.nansum(matrix, axis=1)
    else:
        annual = np.nanmean(matrix, axis=1)
    annual[~complete] = np.nan
    return annual


def analyze_series(
    rows: Iterable[Mapping[str, float]],
    *,
    dataset_id: str,
    variable_id: str,
    region_id: str,
    unit: str,
    unit_per_year: str | None = None,
    product_type: str = "reanalysis",
    window: tuple[int, int] | None = None,
    annual_agg: str = "mean",
    baseline: tuple[int, int] | None = (1991, 2020),
    bh_family: str | None = None,
    with_pettitt: bool = True,
    with_seasonal_strip: bool = True,
) -> dict:
    """Run the full decided pipeline for one variable × one region.

    `rows` yields dicts with year, month, value and optional coverage_fraction.
    Returns a dict in the trends.json shape plus diagnostics under `_debug`.
    """
    matrix, years, _ = _build_matrix(rows, window)

    base = {
        "dataset_id": dataset_id,
        "variable_id": variable_id,
        "region_id": region_id,
        "period_start": None,
        "period_end": None,
        "series_used": "anomaly",
        "trend_direction": "withheld",
        "sen_slope_per_year": None,
        "unit_per_year": unit_per_year or f"{unit}/yr",
        "confidence_interval_95": [None, None],
        "p_value": None,
        "adjusted_p_value": None,
        "adjustment_method": "benjamini_hochberg",
        "significant_at_0_05": False,
        "observation_count": 0,
        "missing_month_count": 0,
        "mean_coverage_fraction": None,
        "method": "seasonal_mann_kendall_hamed_rao + sens_slope",
        "serial_correlation_note": None,
        "caveats": [],
        "withheld_reason": None,
        "product_type": product_type,
        "bh_family": bh_family,
        "verdict": "not_enough_data",
        "effect_size_swings": None,
        "detect_years": None,
        # diagnostics (not part of the verdict, not in the BH family)
        "change_point": None,
        "seasonal_slopes": None,
    }

    if matrix.size == 0:
        base["withheld_reason"] = "no data inside the requested window"
        base["caveats"].append("no observations available")
        return base

    total_cells = matrix.size
    missing_cells = int(np.isnan(matrix).sum())
    base["missing_month_count"] = missing_cells
    base["mean_coverage_fraction"] = float(1.0 - missing_cells / total_cells)

    annual = _annual_series(matrix, annual_agg)
    complete_years = int(np.sum(~np.isnan(annual)))
    base["period_start"] = int(years[0])
    base["period_end"] = int(years[-1])
    base["_debug"] = {
        "years": [int(y) for y in years],
        "complete_years": complete_years,
        "annual": [None if np.isnan(v) else float(v) for v in annual],
    }

    # --- D6 withholding gates ---------------------------------------------
    missing_fraction = missing_cells / total_cells
    if missing_fraction > MAX_MISSING_FRACTION:
        base["withheld_reason"] = (
            f"{missing_fraction:.0%} of months missing; maximum is "
            f"{MAX_MISSING_FRACTION:.0%}"
        )
        return base
    if complete_years < MIN_COMPLETE_YEARS:
        base["withheld_reason"] = (
            f"only {complete_years} complete years; minimum is {MIN_COMPLETE_YEARS}"
        )
        return base

    # --- anomalies ---------------------------------------------------------
    clim_rows = matrix[~np.isnan(annual)]
    if baseline:
        b0, b1 = baseline
        mask = (years >= b0) & (years <= b1) & ~np.isnan(annual)
        clim_rows = matrix[mask] if mask.any() else clim_rows
    climatology = np.nanmean(clim_rows, axis=0)
    anomalies = matrix - climatology
    anomalies = anomalies[~np.isnan(annual)]  # only complete years enter the test
    anomalies_flat = anomalies.ravel()
    anomalies_flat = anomalies_flat[~np.isnan(anomalies_flat)]

    # --- headline: seasonal MK + Hamed–Rao ---------------------------------
    seasonal = seasonal_mk(anomalies)
    hr = hamed_rao_factor(anomalies_flat)
    var_adj = seasonal["var_S"] * hr
    p_adj, z_adj = mk_pvalue(seasonal["S"], var_adj)
    rho = lag1_autocorrelation(anomalies_flat)

    # --- annual sensitivity check -----------------------------------------
    annual_clean = annual[~np.isnan(annual)]
    annual_years = years[~np.isnan(annual)]
    s_annual, var_annual, n_annual = mk_statistic(annual_clean)
    p_annual, _ = mk_pvalue(s_annual, var_annual)

    # --- slope + CI --------------------------------------------------------
    slope = sen_slope(annual_clean, annual_years)
    lo, hi = sen_ci(annual_clean, annual_years, var_s=var_annual)

    base.update(
        {
            "trend_direction": "no_significant_trend",
            "sen_slope_per_year": float(slope) if np.isfinite(slope) else None,
            "confidence_interval_95": [
                float(lo) if np.isfinite(lo) else None,
                float(hi) if np.isfinite(hi) else None,
            ],
            "p_value": p_adj,
            "observation_count": int(n_annual * 12 - missing_cells),
            "serial_correlation_note": (
                f"lag-1 rho = {rho:+.2f}; Hamed–Rao variance factor {hr:.2f}; "
                f"raw seasonal MK p = {seasonal['p_value']:.4f}"
            ),
        }
    )

    if abs(p_adj - seasonal["p_value"]) > 0.0 and np.sign(p_adj - ALPHA_SIGNIFICANT) != np.sign(
        seasonal["p_value"] - ALPHA_SIGNIFICANT
    ):
        base["caveats"].append("sensitive_to_serial_correlation")

    if abs(p_annual - ALPHA_SIGNIFICANT) <= abs(p_adj - ALPHA_SIGNIFICANT):
        pass  # annual check agrees in strength class (informational only)

    base["_debug"].update(
        {
            "seasonal_mk_raw_p": seasonal["p_value"],
            "seasonal_mk_z": seasonal["z"],
            "hamed_rao_factor": hr,
            "lag1_rho": rho,
            "annual_mk_p": p_annual,
            "annual_S": s_annual,
            "annual_var_S": var_annual,
            "n_annual": int(n_annual),
        }
    )

    # --- single-row verdict (recomputed by finalize_lineup in a family) ----
    base["adjusted_p_value"] = float(p_adj)
    base["significant_at_0_05"] = bool(p_adj < ALPHA_SIGNIFICANT)
    base["verdict"] = verdict_from_p(p_adj, withheld=False)
    if base["verdict"] == "significant" and np.isfinite(slope):
        base["trend_direction"] = "increasing" if slope > 0 else "decreasing"
    else:
        base["trend_direction"] = "no_significant_trend"

    # --- effect size and detectability ------------------------------------
    annual_sd = float(np.std(annual_clean, ddof=1)) if annual_clean.size > 1 else float("nan")
    base["effect_size_swings"] = effect_size_swings(slope, int(annual_clean.size), annual_sd)
    # contract (doc 04): detectability is only filled when the verdict is not significant
    detect = (
        None
        if base["verdict"] == "significant"
        else detectability_years(anomalies_flat, slope)
    )
    if detect is not None and detect <= int(annual_clean.size):
        # The record is already longer than the length needed under stationary
        # AR(1) noise, yet the test did not reject. Showing "needs N years"
        # would contradict the record in front of the reader; the honest
        # statement is that the record is long enough and the trend is absent.
        base["caveats"].append("record_long_enough_but_not_significant")
        detect = None
    base["detect_years"] = detect

    if with_pettitt:
        pettitt = pettitt_test(annual_clean, annual_years)
        if pettitt:
            base["change_point"] = pettitt
            if pettitt["p_value"] < ALPHA_SIGNIFICANT and base["verdict"] != "significant":
                base["caveats"].append("level_shift_detected")

    if with_seasonal_strip:
        base["seasonal_slopes"] = seasonal_slopes(anomalies, years[~np.isnan(annual)])

    return base


def finalize_lineup(rows: Sequence[dict]) -> list[dict]:
    """Apply BH across a lineup, set adjusted p, verdict and ranking (D23, NAS-30).

    Withheld rows never enter the family and never receive a p-value.
    Sorted by adjusted p, then by descending effect size.
    """
    tested = [r for r in rows if r.get("p_value") is not None]
    if tested:
        rejected = benjamini_hochberg([r["p_value"] for r in tested])
        m = len(tested)
        order = np.argsort([r["p_value"] for r in tested])
        adjusted = np.empty(m, dtype=float)
        previous = 1.0
        for rank_pos in range(m - 1, -1, -1):
            idx = order[rank_pos]
            candidate = tested[idx]["p_value"] * m / (rank_pos + 1)
            previous = min(previous, candidate)
            adjusted[idx] = min(1.0, previous)
        for row, adj, rej in zip(tested, adjusted, rejected, strict=True):
            row["adjusted_p_value"] = float(adj)
            row["significant_at_0_05"] = bool(rej)
            row["verdict"] = verdict_from_p(adj, withheld=False)
            row["trend_direction"] = (
                "increasing"
                if rej and (row["sen_slope_per_year"] or 0) > 0
                else "decreasing"
                if rej
                else "no_significant_trend"
            )

    for row in rows:
        if row.get("p_value") is None:
            row["verdict"] = "not_enough_data"
            row["adjusted_p_value"] = None

    def sort_key(row: dict):
        p = row.get("adjusted_p_value")
        eff = row.get("effect_size_swings")
        return (
            1 if p is None else 0,
            p if p is not None else 1.0,
            -(eff if eff is not None else 0.0),
        )

    return sorted(rows, key=sort_key)
