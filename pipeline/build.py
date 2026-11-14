"""Build analysis-ready monthly series from Giovanni exports (Linear NAS-7).

Reads one Giovanni area-averaged CSV, converts units, keeps only complete
calendar years, and writes:

    data/processed/<dataset_id>/<region_id>.parquet   (Linear doc 04 §1 columns)
    data/processed/<dataset_id>/provenance.json       (product, box, transformations)

Usage:
    uv run python -m pipeline.build data/raw/t2m_ireland.csv \\
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

from pipeline.giovanni import read_giovanni_csv
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
    "quality_summary",
    "source",
]

COVERAGE_NOTE = (
    "Giovanni area-averaged series: per-cell QA counts are not reported, so the coverage "
    "columns are null until a gridded subset supplies them"
)


def complete_years(frame: pd.DataFrame) -> list[int]:
    """Return the years that contain all twelve months of data."""
    counted = frame.groupby(frame["timestamp"].dt.year)["value"].count()
    return sorted(int(year) for year, months in counted.items() if months == 12)


def trim_to_complete_years(
    frame: pd.DataFrame,
    start_year: int | None = None,
    end_year: int | None = None,
) -> pd.DataFrame:
    """Keep only whole calendar years, never a partial first or last year."""
    years = complete_years(frame)
    if not years:
        raise ValueError("series has no complete calendar year")
    first, last = years[0], years[-1]
    if end_year is not None and end_year > last:
        raise ValueError(f"end year {end_year} is later than the last complete year {last}")
    start = first if start_year is None else max(start_year, first)
    end = last if end_year is None else end_year
    keep = [year for year in years if start <= year <= end]
    if not keep:
        raise ValueError(f"no complete year between {start} and {end}")
    trimmed = frame[frame["timestamp"].dt.year.isin(keep)]
    return trimmed.sort_values("timestamp").reset_index(drop=True)


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
) -> tuple[Path, Path]:
    """Run the whole conversion for one CSV and return (parquet, provenance) paths."""
    raw = read_giovanni_csv(csv_path)
    raw = raw.dropna(subset=["value"]).reset_index(drop=True)
    converted = raw.assign(
        value=convert(
            raw.set_index("timestamp")["value"],
            native_unit,
            output_unit,
            index=pd.DatetimeIndex(raw["timestamp"]),
        ).to_numpy()
    )
    trimmed = trim_to_complete_years(converted, start_year=start_year, end_year=end_year)

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
        "Giovanni comment/header block skipped",
        f"unit conversion {native_unit} -> {output_unit}"
        if canonical_unit(native_unit) != canonical_unit(output_unit)
        else f"unit unchanged ({native_unit})",
        "rows without a value dropped",
        "kept complete calendar years only",
        "mapped to the doc 04 processed-series columns",
        "anomaly left null: climatology and anomalies belong to analysis/",
    ]

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
            "access_route": "NASA GES DISC / Giovanni",
            "variable_field": giovanni_variable_id,
            "scale_factor": 1.0,
            "native_unit": native_unit,
            "output_unit": output_unit,
            "spatial_resolution": spatial_resolution,
            "period_start": first.date().isoformat(),
            "period_end": last.date().isoformat(),
            "qa_rules": [
                "Giovanni area-averaged time series, monthly",
                "no mixing of product versions inside one series",
                "complete calendar years only",
            ],
            "region_source": "Linear doc 11 §3 box, entered in Giovanni",
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
            "observations": int(len(trimmed)),
            "transformations": transformations,
        },
    )
    return parquet, provenance


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Giovanni CSV -> contract-ready monthly series")
    parser.add_argument("csv", type=Path, help="Giovanni area-averaged CSV export")
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
    parser.add_argument("--access-date", default=date.today().isoformat())
    parser.add_argument("--start-year", type=int, default=None)
    parser.add_argument("--end-year", type=int, default=None)
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
    )
    print(f"wrote {parquet}")
    print(f"wrote {provenance}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
