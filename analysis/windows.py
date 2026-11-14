"""
Time Machine windows (NAS-29)
=============================
Precomputes the trend for **every** start/end year pair at least
`min_window_years` long, so the UI slider only looks up a result and never
computes statistics in the browser (doc 04, schema 2b).

Why this is not just a loop over `analyze_series`
--------------------------------------------------
For a 45-year record there are 666 windows. Re-running the seasonal
Mann-Kendall from scratch costs O(n³); extending a window by one year only
adds the new year's 12 months against everything already inside it, which is
O(n²) per starting year. Same numbers, ~100× less work.

Consistency rules (must match `stats.analyze_series`)
-----------------------------------------------------
* input is the **monthly anomaly matrix** (baseline applied once, upstream)
* only years with all 12 months present enter — same rule as the headline
* variance is tie-corrected per calendar month, then inflated by the
  Hamed–Rao factor of the window's own residuals (D7)
* slope and CI come from the **annual** aggregate, exactly like the headline
* verdict labels come from the adjusted p of the window's lineup family (D23)
* a window **never spans a year that was dropped for missing months** (NAS-59)

Full-window coverage (NAS-59)
-----------------------------
An incomplete year cannot enter a window, exactly as it cannot enter the
headline. That used to hide a second problem: with interior years dropped, a
window 1981–2025 could be computed from 42 years and still be labelled as the
whole span. The JSON contract has no field to flag that, so such windows are
**not emitted**; the caller gets the count in `report` and the run log says how
many were skipped. `require_full_coverage=False` restores the old behaviour for
experiments and tests, never for shipped results.

BH family: one family **per window**, across the five variables — not across
windows. Correcting across 666 windows would make every result vanish.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

import numpy as np

from analysis import stats as tl


def _complete(matrix: np.ndarray) -> np.ndarray:
    return ~np.isnan(matrix).any(axis=1)


def _tie_variance(column: np.ndarray) -> float:
    """Tie-corrected Var(S) for one season's values (same formula as stats.mk_statistic)."""
    values = column[~np.isnan(column)]
    n = values.size
    if n < 3:
        return 0.0
    _, counts = np.unique(values, return_counts=True)
    ties = counts[counts > 1].astype(float)
    return float((n * (n - 1) * (2 * n + 5) - np.sum(ties * (ties - 1) * (2 * ties + 5))) / 18.0)


def _annual(matrix: np.ndarray, agg: str) -> np.ndarray:
    if agg == "sum":
        return np.nansum(matrix, axis=1)
    return np.nanmean(matrix, axis=1)


def build_windows(
    anomaly_matrix: np.ndarray,
    years: Sequence[int],
    *,
    min_window_years: int = 10,
    annual_agg: str = "mean",
    alpha_verdict: float = tl.ALPHA_SIGNIFICANT,
    require_full_coverage: bool = True,
    report: dict | None = None,
) -> list[dict]:
    """Every window of at least `min_window_years` complete years.

    `anomaly_matrix` must be (years, 12) anomalies with NaN for missing months;
    incomplete years are dropped before windows are formed, and any window that
    would span one of those dropped years is skipped (NAS-59) unless
    `require_full_coverage` is False.

    When `report` is given it is filled with
    `windows_skipped_for_missing_years` and `years_dropped_incomplete`, so the
    shortfall is visible to the caller instead of silently shrinking the output.
    """
    matrix = np.asarray(anomaly_matrix, dtype=float)
    yrs = np.asarray(years, dtype=int)
    if matrix.ndim != 2 or matrix.shape[1] != 12:
        raise ValueError("anomaly_matrix must be (years, 12)")
    if matrix.shape[0] != yrs.size:
        raise ValueError("years must have one entry per matrix row")

    keep = _complete(matrix)
    dropped_years = int((~keep).sum())
    matrix, yrs = matrix[keep], yrs[keep]
    n = matrix.shape[0]

    skipped = 0
    if report is not None:
        report["years_dropped_incomplete"] = dropped_years
        report["windows_skipped_for_missing_years"] = 0
    if n < min_window_years:
        return []

    annual = _annual(matrix, annual_agg)
    out: list[dict] = []

    for i in range(n):
        running_s = 0.0
        for j in range(i + 1, n):
            # add every pair (a, j) with a inside the window
            running_s += float(np.nansum(np.sign(matrix[j] - matrix[i:j])))

            span_years = int(yrs[j] - yrs[i] + 1)
            if span_years < min_window_years:
                continue
            # a dropped interior year means this window is not the span it claims
            if require_full_coverage and span_years != j - i + 1:
                skipped += 1
                continue

            window = matrix[i : j + 1]
            var_s = sum(_tie_variance(window[:, m]) for m in range(12))
            factor = tl.hamed_rao_factor(window.ravel())
            p_raw, _ = tl.mk_pvalue(running_s, var_s * factor)

            annual_window = annual[i : j + 1]
            slope = tl.sen_slope(annual_window, yrs[i : j + 1])
            s_annual, var_annual, _ = tl.mk_statistic(annual_window)
            lo, hi = tl.sen_ci(annual_window, yrs[i : j + 1], var_s=var_annual)

            out.append(
                {
                    "start": int(yrs[i]),
                    "end": int(yrs[j]),
                    "n_years": int(j - i + 1),
                    "sen_slope_per_year": float(slope) if np.isfinite(slope) else None,
                    "confidence_interval_95": [
                        float(lo) if np.isfinite(lo) else None,
                        float(hi) if np.isfinite(hi) else None,
                    ],
                    "p_value": float(p_raw),
                    "adjusted_p_value": None,
                    "verdict": tl.verdict_from_p(p_raw, withheld=False),
                    "_debug": {
                        "S": running_s,
                        "var_S": var_s,
                        "hamed_rao_factor": factor,
                        "annual_S": s_annual,
                        "annual_var_S": var_annual,
                    },
                }
            )

    if report is not None:
        report["windows_skipped_for_missing_years"] = skipped
    return out


def _bh_adjusted(pvals: Sequence[float]) -> np.ndarray:
    """BH adjusted p-values (monotone step-up), aligned with the input order."""
    p = np.asarray(list(pvals), dtype=float)
    m = p.size
    if m == 0:
        return np.zeros(0)
    order = np.argsort(p)
    adjusted = np.empty(m, dtype=float)
    running = 1.0
    for rank_pos in range(m - 1, -1, -1):
        idx = order[rank_pos]
        running = min(running, p[idx] * m / (rank_pos + 1))
        adjusted[idx] = min(1.0, running)
    return adjusted


def finalize_window_family(rows: Iterable[Mapping]) -> list[dict]:
    """Apply BH **within each window** across variables, then set verdicts.

    `rows` are window dicts that also carry `variable_id` and `region_id`.
    Returns a new list sorted by start, end, then adjusted p.
    """
    grouped: dict[tuple[int, int], list[dict]] = {}
    for row in rows:
        item = dict(row)
        grouped.setdefault((item["start"], item["end"]), []).append(item)

    out: list[dict] = []
    for key in sorted(grouped):
        family = grouped[key]
        adjusted = _bh_adjusted([r["p_value"] for r in family])
        for row, adj in zip(family, adjusted, strict=True):
            row["adjusted_p_value"] = float(adj)
            row["verdict"] = tl.verdict_from_p(adj, withheld=False)
        out.extend(family)

    out.sort(key=lambda r: (r["start"], r["end"], r.get("variable_id", "")))
    return out


def contract_rows(rows: Iterable[Mapping], *, ndigits: int = 6) -> list[dict]:
    """Strip test-only fields and round floats for the shipped JSON (schema 2b).

    `_debug` roughly doubles the payload and is not part of the contract.
    """
    out: list[dict] = []
    for row in rows:
        item = {k: v for k, v in row.items() if not k.startswith("_")}
        for key in ("sen_slope_per_year", "p_value", "adjusted_p_value"):
            if item.get(key) is not None:
                item[key] = round(float(item[key]), ndigits)
        ci = item.get("confidence_interval_95")
        if ci:
            item["confidence_interval_95"] = [
                None if bound is None else round(float(bound), ndigits) for bound in ci
            ]
        out.append(item)
    return out


def windows_for_series(
    rows: Iterable[Mapping[str, float]],
    *,
    variable_id: str,
    region_id: str,
    window: tuple[int, int] | None = None,
    baseline: tuple[int, int] | None = (1991, 2020),
    annual_agg: str = "mean",
    min_window_years: int = 10,
    require_full_coverage: bool = True,
    report: dict | None = None,
) -> list[dict]:
    """Convenience wrapper: rows of {year, month, value, coverage} -> windows."""
    matrix, yrs, _ = tl._build_matrix(rows, window)  # same assembly as the headline
    if matrix.size == 0:
        return []

    keep = _complete(matrix)
    if not keep.any():
        return []

    clim_source = matrix[keep]
    if baseline:
        b0, b1 = baseline
        mask = (yrs >= b0) & (yrs <= b1) & keep
        if mask.any():
            clim_source = matrix[mask]
    climatology = np.nanmean(clim_source, axis=0)
    anomalies = matrix - climatology

    built = build_windows(
        anomalies,
        yrs,
        min_window_years=min_window_years,
        annual_agg=annual_agg,
        require_full_coverage=require_full_coverage,
        report=report,
    )
    for row in built:
        row["variable_id"] = variable_id
        row["region_id"] = region_id
    return built


def verify_window(
    anomaly_matrix: np.ndarray,
    years: Sequence[int],
    start: int,
    end: int,
    *,
    annual_agg: str = "mean",
) -> dict:
    """Direct O(n³) recomputation of one window — used by the tests, not the pipeline."""
    matrix = np.asarray(anomaly_matrix, dtype=float)
    yrs = np.asarray(years, dtype=int)
    keep = _complete(matrix)
    matrix, yrs = matrix[keep], yrs[keep]
    sel = (yrs >= start) & (yrs <= end)
    sub = matrix[sel]
    sub_years = yrs[sel]

    seasonal = tl.seasonal_mk(sub)
    factor = tl.hamed_rao_factor(sub.ravel())
    p_raw, _ = tl.mk_pvalue(seasonal["S"], seasonal["var_S"] * factor)

    annual = _annual(sub, annual_agg)
    slope = tl.sen_slope(annual, sub_years)
    _, var_annual, _ = tl.mk_statistic(annual)
    lo, hi = tl.sen_ci(annual, sub_years, var_s=var_annual)

    return {
        "start": int(sub_years[0]),
        "end": int(sub_years[-1]),
        "p_value": float(p_raw),
        "sen_slope_per_year": float(slope),
        "confidence_interval_95": [float(lo), float(hi)],
        "S": seasonal["S"],
    }
