"""Build analysis-ready monthly series from NASA source CSVs (Linear NAS-7).

Reads one area-averaged CSV, checks its declared unit against the
registry, converts units, clips to the variable's registered window, and writes:

    data/processed/<dataset_id>/<region_id>.parquet   (Linear doc 04 §1 columns)
    data/processed/<dataset_id>/provenance.json       (product, box, transformations)

Missing months stay in the series as null rows. A gap is a fact about the data,
and dropping the whole year around it would quietly shorten the record; only the
statistics layer decides what a missing month means.

Usage:
    uv run python -m pipeline.build data/raw/t2m_ireland_harmony.csv \\
        --variable-id t2m --region-id ireland --analyzable-region "..."
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.giovanni import read_giovanni_csv, read_giovanni_unit
from pipeline.regions import box_string, get_region
from pipeline.registry import VARIABLES
from pipeline.units import canonical_unit, convert

CONTRACT_COLUMNS = [
    "dataset_id",
    "variable_id",
    "region_id",
    "timestamp",
    "value",
    "unit",
    "anomaly",
    "valid_cell_count",
    "total_cell_count",
    "coverage_fraction",
    "n_valid_days",
    "quality_summary",
    "source",
]

COVERAGE_NOTE = (
    "Area-averaged series: per-cell QA counts are not reported, so the coverage columns "
    "are null until a gridded subset supplies them"
)


class UnitMismatchError(ValueError):
    """Raised when a CSV's declared unit disagrees with the unit we expect."""


def check_declared_unit(declared: str | None, expected: str) -> None:
    """Fail loudly when Giovanni's own unit line contradicts the registry.

    Without this, an export already delivered in mm/month would be multiplied by
    hours-per-day and days-in-month a second time, and every IMERG number would be
    silently too large. A missing unit line is tolerated: some exports omit it, and
    provenance records that the file declared nothing.
    """
    if declared is None:
        return
    if canonical_unit(declared) != canonical_unit(expected):
        raise UnitMismatchError(
            f"the CSV declares unit {declared!r} but this row expects {expected!r}; "
            f"if Giovanni already converted, pass --native-unit {declared!r}, "
            f"otherwise re-download the export in {expected!r}"
        )


def window_for(variable_id: str) -> tuple[int, int]:
    """Return the registered (start, end) year for a variable."""
    spec = VARIABLES.get(variable_id)
    if spec is None:
        raise KeyError(f"unknown variable_id {variable_id!r}; known: {', '.join(VARIABLES)}")
    return spec.start_year, spec.end_year


def trim_to_window(
    frame: pd.DataFrame,
    *,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """Clip to the registered window and keep every month inside it as a row.

    Rows outside the window are dropped (T2M exports begin in 1980; the series
    starts in 1981). Between the first and last month that the export covers,
    months with no row are inserted as nulls rather than dropping their year.
    """
    if start_year > end_year:
        raise ValueError(f"start year {start_year} is later than end year {end_year}")

    window_start = pd.Timestamp(year=start_year, month=1, day=1)
    window_end = pd.Timestamp(year=end_year, month=12, day=1)
    timestamps = frame["timestamp"]
    first = max(timestamps.min(), window_start)
    last = min(timestamps.max(), window_end)
    if first > last:
        raise ValueError(f"no rows between {start_year} and {end_year}")

    inside = frame[(timestamps >= first) & (timestamps <= last)]
    index = pd.date_range(first, last, freq="MS")

    series = inside.set_index("timestamp")["value"].reindex(index).astype("float64")
    series.index.name = "timestamp"
    out = series.reset_index()
    if out["value"].notna().sum() == 0:
        raise ValueError(f"no values between {start_year} and {end_year}")
    return out


def contract_frame(
    values: pd.DataFrame,
    *,
    dataset_id: str,
    variable_id: str,
    region_id: str,
    unit: str,
    source: str,
) -> pd.DataFrame:
    """Shape a monthly frame into the Linear doc 04 §1 column list."""
    count = len(values)
    return pd.DataFrame(
        {
            "dataset_id": [dataset_id] * count,
            "variable_id": [variable_id] * count,
            "region_id": [region_id] * count,
            "timestamp": values["timestamp"].dt.date,
            "value": values["value"].astype("float64"),
            "unit": [unit] * count,
            "anomaly": pd.array([pd.NA] * count, dtype="Float64"),
            "valid_cell_count": pd.array([pd.NA] * count, dtype="Int64"),
            "total_cell_count": pd.array([pd.NA] * count, dtype="Int64"),
            "coverage_fraction": pd.array([pd.NA] * count, dtype="Float64"),
            "n_valid_days": pd.array([pd.NA] * count, dtype="Int64"),
            "quality_summary": [COVERAGE_NOTE] * count,
            "source": [source] * count,
        }
    )


def write_series(frame: pd.DataFrame, out_root: Path, dataset_id: str, region_id: str) -> Path:
    """Write one Parquet file and return its path."""
    target = out_root / dataset_id
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{region_id}.parquet"
    frame.to_parquet(path, index=False)
    return path


def write_provenance(
    out_root: Path,
    dataset_id: str,
    dataset_fields: dict[str, Any],
    region_entry: dict[str, Any],
) -> Path:
    """Merge this series into the dataset's provenance.json."""
    target = out_root / dataset_id
    target.mkdir(parents=True, exist_ok=True)
    path = target / "provenance.json"
    existing: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    merged = {**existing, **dataset_fields}
    regions = dict(existing.get("regions", {}))
    regions[region_entry["region_id"]] = region_entry
    merged["regions"] = regions
    path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return path


def sha256_of(path: Path) -> str:
    """Fingerprint the source CSV so a processed series can be traced back."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(
    csv_path: Path,
    *,
    dataset_id: str,
    variable_id: str,
    region_id: str,
    product: str,
    version: str,
    native_unit: str,
    output_unit: str,
    spatial_resolution: str,
    giovanni_variable_id: str,
    requested_box: str | None,
    analyzable_region: str | None,
    permalink: str | None,
    access_date: str,
    start_year: int | None,
    end_year: int | None,
    out_root: Path,
    access_route: str = "NASA GES DISC / Giovanni",
    allow_short: bool = False,
) -> tuple[Path, Path]:
    """Run the whole conversion for one CSV and return (parquet, provenance) paths."""
    spec_start, spec_end = window_for(variable_id)
    start = spec_start if start_year is None else start_year
    end = spec_end if end_year is None else end_year

    declared = read_giovanni_unit(csv_path)
    check_declared_unit(declared, native_unit)

    raw = read_giovanni_csv(csv_path)
    values = pd.Series(
        raw["value"].astype("float64").to_numpy(),
        index=pd.DatetimeIndex(raw["timestamp"]),
    )
    converted = raw.assign(
        value=convert(values, native_unit, output_unit, index=values.index).to_numpy()
    )
    trimmed = trim_to_window(converted, start_year=start, end_year=end)

    # A file that stops before the window ends would otherwise produce a short
    # series that looks perfectly fine downstream. The window is the promise; a
    # series that cannot keep it has to be an explicit decision.
    window_first = pd.Timestamp(year=start, month=1, day=1)
    window_last = pd.Timestamp(year=end, month=12, day=1)
    covered_first = trimmed["timestamp"].iloc[0]
    covered_last = trimmed["timestamp"].iloc[-1]
    shortfall = []
    if covered_first > window_first:
        shortfall.append(f"starts {covered_first:%Y-%m} not {start}-01")
    if covered_last < window_last:
        shortfall.append(f"ends {covered_last:%Y-%m} not {end}-12")
    if shortfall and not allow_short:
        raise ValueError(
            f"series does not cover the registered window {start}-01..{end}-12 "
            f"({'; '.join(shortfall)}); pass --allow-short to accept a short series"
        )
    if shortfall:
        full_index = pd.date_range(window_first, window_last, freq="MS")
        trimmed = (
            trimmed.set_index("timestamp")["value"]
            .reindex(full_index)
            .rename_axis("timestamp")
            .reset_index()
        )

    null_months = int(trimmed["value"].isna().sum())
    observed = int(len(trimmed) - null_months)

    source = f"{product} v{version}".replace(" vv", " v")
    frame = contract_frame(
        trimmed,
        dataset_id=dataset_id,
        variable_id=variable_id,
        region_id=region_id,
        unit=output_unit,
        source=source,
    )

    transformations = [
        "source metadata and header rows skipped",
        f"unit conversion {native_unit} -> {output_unit}"
        if canonical_unit(native_unit) != canonical_unit(output_unit)
        else f"unit unchanged ({native_unit})",
        f"CSV declared unit {declared!r} matched the expected {native_unit!r}"
        if declared is not None
        else f"CSV declared no unit; expected {native_unit!r} assumed",
        f"clipped to the registered window {start}-01 to {end}-12",
        f"missing months kept as null rows ({null_months} in this series)",
        f"short series allowed: {'; '.join(shortfall)}"
        if shortfall
        else "series covers the full registered window",
        "mapped to the doc 04 processed-series columns",
        "anomaly left null: climatology and anomalies belong to analysis/",
    ]

    if "giovanni" in access_route.lower():
        qa_rules = [
            "Giovanni area-averaged time series, monthly",
            "no mixing of product versions inside one series",
            "registered variable window, whole calendar years",
            "missing months kept as null rows",
            "CSV declared unit must match the expected native unit",
        ]
        region_source = "Linear doc 11 §3 box, entered in Giovanni"
    else:
        # NAS-64 review: a locally reduced field must not carry Giovanni boilerplate.
        qa_rules = [
            "area mean computed locally from the source field, monthly",
            "no mixing of product versions inside one series",
            "registered variable window, whole calendar years",
            "missing months kept as null rows",
            "CSV declared unit must match the expected native unit",
        ]
        region_source = (
            f"Linear doc 11 §3 box, applied to the locally averaged field ({access_route})"
        )

    parquet = write_series(frame, out_root, dataset_id, region_id)
    first, last = trimmed["timestamp"].iloc[0], trimmed["timestamp"].iloc[-1]
    provenance = write_provenance(
        out_root,
        dataset_id,
        {
            "dataset_id": dataset_id,
            "product": product,
            "version": version,
            "doi_or_url": permalink or "",
            "access_date": access_date,
            "access_route": access_route,
            "variable_field": giovanni_variable_id,
            "scale_factor": 1.0,
            "native_unit": native_unit,
            "output_unit": output_unit,
            "spatial_resolution": spatial_resolution,
            "period_start": first.date().isoformat(),
            "period_end": last.date().isoformat(),
            "qa_rules": qa_rules,
            "region_source": region_source,
            "transformations": transformations,
        },
        {
            "region_id": region_id,
            "requested_box": requested_box or "",
            "analyzable_region": analyzable_region or "",
            "period_start": first.date().isoformat(),
            "period_end": last.date().isoformat(),
            "giovanni_variable_id": giovanni_variable_id,
            "permalink": permalink or "",
            "source_csv": csv_path.name,
            "source_csv_sha256": sha256_of(csv_path),
            "observations": observed,
            "transformations": transformations,
        },
    )
    return parquet, provenance


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NASA source CSV -> contract-ready monthly series")
    parser.add_argument("csv", type=Path, help="area-averaged NASA source CSV")
    parser.add_argument("--variable-id", required=True, help=f"one of: {', '.join(VARIABLES)}")
    parser.add_argument("--region-id", required=True, help="region_id from pipeline/regions.json")
    parser.add_argument("--dataset-id", default=None)
    parser.add_argument("--product", default=None)
    parser.add_argument("--version", default=None)
    parser.add_argument("--native-unit", default=None, help="unit as delivered by Giovanni")
    parser.add_argument("--unit", default=None, help="unit to store and display")
    parser.add_argument("--spatial-resolution", default=None)
    parser.add_argument("--giovanni-variable-id", default=None)
    parser.add_argument(
        "--requested-box", default=None, help="W,S,E,N (default: from regions.json)"
    )
    parser.add_argument("--analyzable-region", default=None, help="region string Giovanni reports")
    parser.add_argument("--permalink", default=None)
    parser.add_argument(
        "--access-route",
        default=None,
        help="how the bytes were obtained (default: NASA GES DISC / Giovanni)",
    )
    parser.add_argument("--access-date", default=date.today().isoformat())
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="override the registered window start (default: per variable, D21)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="override the registered window end (default: per variable, D21)",
    )
    parser.add_argument(
        "--allow-short",
        action="store_true",
        help="accept a series that does not reach both ends of the window (padded with nulls)",
    )
    parser.add_argument("--out", type=Path, default=Path("data/processed"))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    spec = VARIABLES.get(args.variable_id)
    if spec is None:
        parser.error(f"unknown --variable-id {args.variable_id!r}; known: {', '.join(VARIABLES)}")

    dataset_id = args.dataset_id or spec.dataset_id
    requested_box = args.requested_box
    if requested_box is None:
        try:
            requested_box = box_string(get_region(args.region_id))
        except KeyError as error:
            parser.error(str(error))

    try:
        parquet, provenance = build(
            args.csv,
            dataset_id=dataset_id,
            variable_id=args.variable_id,
            region_id=args.region_id,
            product=args.product or spec.product,
            version=args.version or spec.version,
            native_unit=args.native_unit or spec.native_unit,
            output_unit=args.unit or spec.output_unit,
            spatial_resolution=args.spatial_resolution or spec.spatial_resolution,
            giovanni_variable_id=args.giovanni_variable_id or spec.giovanni_variable_id,
            requested_box=requested_box,
            analyzable_region=args.analyzable_region,
            permalink=args.permalink,
            access_date=args.access_date,
            start_year=args.start_year,
            end_year=args.end_year,
            out_root=args.out,
            access_route=args.access_route or "NASA GES DISC / Giovanni",
            allow_short=args.allow_short,
        )
    except (UnitMismatchError, ValueError) as error:
        parser.error(str(error))
    print(f"wrote {parquet}")
    print(f"wrote {provenance}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
