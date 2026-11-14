"""Analysis entry point: processed Parquet -> contract results (NAS-12, NAS-28/30).

Reads the pipeline's monthly series, runs the decided statistics, and applies
BH **twice**, because the contract has two families (D23): within each region's
lineup, and within each variable across regions for the compare view. The same
region and variable therefore carries two adjusted p-values — the Lineup one in
`lineup/<region>.json`, the compare one in `<dataset_id>/trends.json`. The API
serves `/trend` from the lineup file so a detail card always matches the Lineup
verdict, and `/compare` from trends.json.

The three files the API and the static export read:

    data/results/<dataset_id>/trends.json              (doc 04 schema 2)
    data/results/lineup/<region_id>.json               (doc 04 schema 2a)
    data/results/windows/<dataset_id>/<region_id>.json (doc 04 schema 2b)

Every output is validated with the backend's Pydantic models before it is
written, so a contract violation fails here rather than in the API.

Usage:
    python -m analysis.run --region ireland
    python -m analysis.run                      # every region with data
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from analysis import stats as tl
from analysis import windows as tw
from pipeline.regions import APP_REGIONS

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
RESULTS = REPO_ROOT / "data" / "results"

# Plain-language line for each Lineup row (doc 04 schema 2a requires it and the
# catalogue does not carry it yet).
DEFINITIONS: dict[str, str] = {
    "t2m": "How warm the air is at about head height",
    "soil_moisture_0_5": "How much water is held in the top layer of soil",
    "evapotranspiration": "Water leaving the land through plants and evaporation",
    "precipitation": "How much rain and snow falls",
    "aerosol": "How much dust and smoke is in the air",
    "no2": "Nitrogen dioxide from traffic, industry and fires",
}

PRODUCT_TYPE: dict[str, str] = {
    "t2m": "reanalysis",
    "aerosol": "reanalysis",
    "soil_moisture_0_5": "reanalysis",
    "evapotranspiration": "reanalysis",
    "precipitation": "reanalysis",
    "no2": "satellite",
}

# Precipitation is a monthly total, so its annual aggregate is a sum; every
# other row is a state, so the annual mean is the right aggregate.
ANNUAL_AGG: dict[str, str] = {"precipitation": "sum"}

# The Sen slope is fitted to the annual aggregate, so for a summed variable its
# unit is the annual total, not the monthly value the series is stored in.
SLOPE_BASE_UNIT: dict[str, str] = {"precipitation": "mm (annual total)"}

BASELINE = (1991, 2020)
MIN_WINDOW_YEARS = 10


def _backend_models():
    """Import the contract models, adding backend/ to the path when run as a script."""
    try:
        from app.models.results import Lineup, TrendResult, Windows  # noqa: F401
    except ImportError:  # pragma: no cover - exercised when running outside pytest
        sys.path.insert(0, str(REPO_ROOT / "backend"))
        from app.models.results import Lineup, TrendResult, Windows  # noqa: F401
    return TrendResult, Lineup, Windows


def load_series(parquet: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = pd.read_parquet(parquet)
    if frame.empty:
        raise ValueError(f"{parquet} is empty")
    return frame, {
        "dataset_id": str(frame["dataset_id"].iloc[0]),
        "variable_id": str(frame["variable_id"].iloc[0]),
        "region_id": str(frame["region_id"].iloc[0]),
        "unit": str(frame["unit"].iloc[0]),
    }


def to_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for record in frame.itertuples(index=False):
        stamp = pd.Timestamp(record.timestamp)
        coverage = getattr(record, "coverage_fraction", None)
        rows.append(
            {
                "year": stamp.year,
                "month": stamp.month,
                "value": None if pd.isna(record.value) else float(record.value),
                "coverage_fraction": (
                    1.0 if coverage is None or pd.isna(coverage) else float(coverage)
                ),
            }
        )
    return rows


def trend_payload(
    *,
    row: dict[str, Any],
    meta: dict[str, Any],
    region_id: str,
    bh_family: str,
) -> dict[str, Any]:
    """Map one analysis row onto doc 04 schema 2 (still unvalidated)."""
    withheld = row["verdict"] == "not_enough_data"
    unit = meta["unit"]
    return {
        "dataset_id": meta["dataset_id"],
        "variable_id": meta["variable_id"],
        "region_id": region_id,
        "period_start": date(int(row["period_start"]), 1, 1),
        "period_end": date(int(row["period_end"]), 12, 1),
        "series_used": "anomaly",
        "trend_direction": "withheld" if withheld else row["trend_direction"],
        "sen_slope_per_year": None if withheld else row["sen_slope_per_year"],
        "unit_per_year": f"{SLOPE_BASE_UNIT.get(meta['variable_id'], unit)}/yr",
        "confidence_interval_95": None if withheld else tuple(row["confidence_interval_95"]),
        "p_value": None if withheld else row["p_value"],
        "adjusted_p_value": None if withheld else row["adjusted_p_value"],
        "adjustment_method": "benjamini_hochberg",
        "significant_at_0_05": False if withheld else bool(row["adjusted_p_value"] < 0.05),
        "observation_count": int(row["observation_count"]),
        "missing_month_count": int(row["missing_month_count"]),
        "mean_coverage_fraction": float(row["mean_coverage_fraction"] or 0.0),
        "method": "seasonal_mann_kendall_hamed_rao + sens_slope",
        "serial_correlation_note": row["serial_correlation_note"] or "",
        "caveats": list(row["caveats"]),
        "withheld_reason": row["withheld_reason"],
        "product_type": PRODUCT_TYPE.get(meta["variable_id"], "reanalysis"),
        "bh_family": bh_family,
        "verdict": row["verdict"],
        # the model rejects effect size and detectability on withheld rows
        "effect_size_swings": None if withheld else row["effect_size_swings"],
        "detect_years": None if withheld else row["detect_years"],
        # D25 diagnostics: descriptive only, never part of a BH family, and the
        # model rejects them on withheld rows just like the fields above.
        "change_point": None if withheld else row.get("change_point"),
        "seasonal_slopes": None if withheld else row.get("seasonal_slopes"),
    }


def analyse_region(region: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run every available variable for one region; return (trends, windows)."""
    from pipeline.registry import VARIABLES

    trend_rows: list[dict[str, Any]] = []
    window_rows: list[dict[str, Any]] = []
    family = f"lineup:{region}"

    for parquet in sorted(PROCESSED.glob(f"*/{region}.parquet")):
        frame, meta = load_series(parquet)
        variable_id = meta["variable_id"]
        spec = VARIABLES.get(variable_id)
        if spec is None:
            print(f"skip {parquet}: variable_id {variable_id!r} is not in the registry")
            continue

        rows = to_rows(frame)
        window = (spec.start_year, spec.end_year)
        agg = ANNUAL_AGG.get(variable_id, "mean")

        analysis = tl.analyze_series(
            rows,
            dataset_id=meta["dataset_id"],
            variable_id=variable_id,
            region_id=region,
            unit=meta["unit"],
            product_type=PRODUCT_TYPE.get(variable_id, "reanalysis"),
            window=window,
            baseline=BASELINE,
            annual_agg=agg,
            bh_family=family,
        )
        payload = trend_payload(row=analysis, meta=meta, region_id=region, bh_family=family)
        payload["definition"] = DEFINITIONS.get(variable_id, variable_id)
        payload["sparkline"] = tl.sparkline(
            [v for v in _annual_values(frame, agg) if v is not None]
        )
        trend_rows.append(payload)

        window_report: dict[str, Any] = {}
        built = tw.windows_for_series(
            rows,
            variable_id=variable_id,
            region_id=region,
            window=window,
            baseline=BASELINE,
            annual_agg=agg,
            min_window_years=MIN_WINDOW_YEARS,
            report=window_report,
        )
        skipped = window_report.get("windows_skipped_for_missing_years", 0)
        if skipped or window_report.get("years_dropped_incomplete"):
            print(
                f"  {region}/{variable_id}: dropped "
                f"{window_report.get('years_dropped_incomplete', 0)} incomplete year(s), "
                f"skipped {skipped} windows that would span them"
            )
        for item in built:
            item["dataset_id"] = meta["dataset_id"]
        window_rows.extend(built)

    return trend_rows, window_rows


def _annual_values(frame: pd.DataFrame, agg: str) -> list[float | None]:
    """Annual aggregate per calendar year; None for incomplete years."""
    index = pd.to_datetime(frame["timestamp"])
    series = pd.Series(frame["value"].to_numpy(), index=index)
    out: list[float | None] = []
    for _year, group in series.groupby(series.index.year):
        if len(group) < 12 or group.isna().any():
            out.append(None)
        else:
            out.append(float(group.sum() if agg == "sum" else group.mean()))
    return out


def apply_bh(trends: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """BH within the region's lineup and the schema 2a ranking."""
    ranked = tl.finalize_lineup(trends)
    by_variable = {row["variable_id"]: row for row in ranked}
    for row in trends:
        source = by_variable[row["variable_id"]]
        row["adjusted_p_value"] = source["adjusted_p_value"]
        row["verdict"] = source["verdict"]
        row["significant_at_0_05"] = source["significant_at_0_05"]
        if source["verdict"] == "significant":
            row["trend_direction"] = source["trend_direction"]
            row["detect_years"] = None
        elif source["verdict"] != "not_enough_data":
            row["trend_direction"] = "no_significant_trend"
    return ranked


def apply_compare_family(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """BH within each variable across regions — the family `/compare` validates.

    `CompareResult` requires `bh_family == compare:<variable_id>` with one family
    per variable, so this must run over the rows of **every** region at once.
    Mutates and returns the same row objects; a withheld row stays out of the
    family and keeps null p-values, exactly as in the lineup.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["variable_id"], []).append(row)

    out: list[dict[str, Any]] = []
    for variable_id, family in grouped.items():
        tl.finalize_lineup(family)
        for row in family:
            row["bh_family"] = f"compare:{variable_id}"
            if row["verdict"] == "significant":
                row["detect_years"] = None
        out.extend(family)
    return out


ROW_ONLY_FIELDS = ("definition", "sparkline")


def _trend_only(row: dict[str, Any]) -> dict[str, Any]:
    """Schema 2 forbids unknown fields, so drop the schema 2a row decorations."""
    return {key: value for key, value in row.items() if key not in ROW_ONLY_FIELDS}


def write_outputs(
    *,
    trends: list[dict[str, Any]],
    lineup_rows: list[dict[str, Any]],
    windows: list[dict[str, Any]],
    region: str,
) -> list[Path]:
    TrendResult, Lineup, Windows = _backend_models()
    written: list[Path] = []

    # --- schema 2: one file per dataset ------------------------------------
    by_dataset: dict[str, list[dict]] = {}
    for row in trends:
        by_dataset.setdefault(row["dataset_id"], []).append(row)
    for dataset_id, rows in by_dataset.items():
        target = RESULTS / dataset_id / "trends.json"
        target.parent.mkdir(parents=True, exist_ok=True)

        # trends.json holds one object per region, so a per-region run must
        # replace its own entries and keep every other region's.
        existing: list[dict[str, Any]] = []
        if target.exists():
            existing = json.loads(target.read_text(encoding="utf-8"))
        keep = [row for row in existing if row.get("region_id") != region]

        merged = keep + [
            TrendResult.model_validate(_trend_only(row)).model_dump(mode="json") for row in rows
        ]
        merged.sort(key=lambda row: row["region_id"])
        target.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        written.append(target)

    # --- schema 2a: the ranked lineup -------------------------------------
    lineup = {
        "region_id": region,
        "bh_family": f"lineup:{region}",
        "rows": [
            {
                "dataset_id": row["dataset_id"],
                "variable_id": row["variable_id"],
                "label": LABELS.get(row["variable_id"], row["variable_id"]),
                "definition": row["definition"],
                "product_type": row["product_type"],
                "period_start": row["period_start"],
                "period_end": row["period_end"],
                "sparkline": row["sparkline"],
                "trend": _trend_only(row),
            }
            for row in sorted(lineup_rows, key=_rank_key)
        ],
    }
    validated_lineup = Lineup.model_validate(lineup).model_dump(mode="json")
    target = RESULTS / "lineup" / f"{region}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(validated_lineup, indent=2) + "\n", encoding="utf-8")
    written.append(target)

    # --- schema 2b: windows, one file per dataset -------------------------
    final = tw.finalize_window_family(windows)
    by_dataset_windows: dict[str, list[dict]] = {}
    for row in final:
        by_dataset_windows.setdefault(row["dataset_id"], []).append(row)
    for dataset_id, rows in by_dataset_windows.items():
        # schema 2b forbids extra fields, so drop the grouping keys here
        cleaned = [
            {
                key: item.get(key)
                for key in (
                    "start",
                    "end",
                    "sen_slope_per_year",
                    "confidence_interval_95",
                    "p_value",
                    "adjusted_p_value",
                    "verdict",
                )
            }
            for item in tw.contract_rows(rows)
        ]
        payload = {
            "dataset_id": dataset_id,
            "region_id": region,
            "min_window_years": MIN_WINDOW_YEARS,
            "windows": cleaned,
        }
        validated_windows = Windows.model_validate(payload).model_dump(mode="json")
        target = RESULTS / "windows" / dataset_id / f"{region}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(validated_windows, indent=2) + "\n", encoding="utf-8")
        written.append(target)
    return written


def _rank_key(row: dict[str, Any]):
    p = row.get("adjusted_p_value")
    effect = row.get("effect_size_swings") or 0.0
    return (1 if p is None else 0, p if p is not None else 1.0, -effect)


LABELS: dict[str, str] = {
    "t2m": "Air temperature (2 m)",
    "soil_moisture_0_5": "Soil moisture (0-5 cm)",
    "evapotranspiration": "Evapotranspiration",
    "precipitation": "Precipitation",
    "aerosol": "Aerosol optical depth",
    "no2": "NO2 column (troposphere)",
}


def regions_with_data() -> list[str]:
    on_disk = {path.stem for path in PROCESSED.glob("*/*.parquet")}
    return [region for region in APP_REGIONS if region in on_disk]


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="processed series -> contract results")
    parser.add_argument("--region", default=None, help="one region_id (default: all)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    targets = [args.region] if args.region else regions_with_data()
    if not targets:
        parser.error("no processed parquet files under data/processed")

    bundles: dict[str, dict[str, Any]] = {}
    for region in targets:
        trends, windows = analyse_region(region)
        if not trends:
            print(f"{region}: no analysable series")
            continue
        # two copies: the lineup family and the compare family adjust the same
        # row differently, and both values have to survive to their own file.
        lineup_rows = [dict(row) for row in trends]
        ranked = apply_bh(lineup_rows)
        bundles[region] = {
            "compare": trends,
            "lineup": lineup_rows,
            "ranked": ranked,
            "windows": windows,
        }

    if args.region and bundles:
        print(
            "note: a single-region run leaves one member in each compare family; "
            "run every region before shipping results"
        )

    compare_rows = apply_compare_family(
        [row for bundle in bundles.values() for row in bundle["compare"]]
    )

    for region, bundle in bundles.items():
        own = [row for row in compare_rows if row["region_id"] == region]
        written = write_outputs(
            trends=own,
            lineup_rows=bundle["lineup"],
            windows=bundle["windows"],
            region=region,
        )
        top = bundle["ranked"][0]
        print(
            f"{region}: {len(bundle['compare'])} rows, top = {top['variable_id']} "
            f"({top['verdict']}), {len(bundle['windows'])} windows, {len(written)} files"
        )
        for path in written:
            print(f"  wrote {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
