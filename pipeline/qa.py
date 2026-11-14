"""Check that `data/processed` is what its provenance claims (NAS-41).

Everything downstream trusts three things about a processed series: the unit was
the one the registry promised, the months are the registered window with nothing
silently missing, and the file really came from the raw CSV its provenance names.
This module checks all three, and can rebuild each series from raw to prove the
processed data is reproducible rather than hand-edited.

    python -m pipeline.qa                 # structure, units, windows, source hashes
    python -m pipeline.qa --regenerate    # additionally rebuild from data/raw and compare

Exit codes: 0 clean (warnings allowed), 1 errors found, 2 regeneration mismatch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from pipeline import build as build_module
from pipeline.regions import load_regions
from pipeline.registry import VARIABLES
from pipeline.units import canonical_unit

REQUIRED_DATASET_FIELDS = (
    "dataset_id",
    "product",
    "version",
    "access_date",
    "access_route",
    "variable_field",
    "native_unit",
    "output_unit",
    "spatial_resolution",
    "regions",
)
REQUIRED_REGION_FIELDS = (
    "requested_box",
    "period_start",
    "period_end",
    "source_csv",
    "source_csv_sha256",
)


@dataclass(frozen=True)
class Issue:
    """One finding, tied to the series it belongs to."""

    level: str  # "error" or "warning"
    dataset_id: str
    region_id: str
    message: str

    def __str__(self) -> str:
        where = f"{self.dataset_id}/{self.region_id}" if self.region_id else self.dataset_id
        return f"{self.level.upper():7s} {where:44s} {self.message}"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _same_day(left: object, right: object) -> bool:
    """Whether two date-like values name the same calendar day, whatever the format."""
    return str(left)[:10] == str(right)[:10]


def _check_window(timestamps: pd.Series, start_year: int, end_year: int) -> list[str]:
    """Every month of the registered window, once, in order."""
    problems: list[str] = []
    expected = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-01", freq="MS")
    observed = pd.DatetimeIndex(timestamps)
    if observed.duplicated().any():
        problems.append("duplicate months")
    if len(observed) != len(expected):
        problems.append(f"{len(observed)} rows, window has {len(expected)} months")
    elif not observed.equals(expected):
        problems.append("months are not the continuous registered window")
    return problems


def check_series(
    dataset_id: str,
    region_id: str,
    frame: pd.DataFrame,
    entry: dict,
    spec,
    raw_root: Path,
) -> list[Issue]:
    """Checks for one processed series against its provenance entry."""
    issues: list[Issue] = []

    def add(level: str, message: str) -> None:
        issues.append(Issue(level, dataset_id, region_id, message))

        # A schema defect must not hide the rest: an old file can also have a stale

    # source hash, and reporting one problem at a time makes the QA useless.
    missing = [column for column in build_module.CONTRACT_COLUMNS if column not in frame.columns]
    if missing:
        add("error", f"missing contract columns: {', '.join(missing)}")
    extra = [column for column in frame.columns if column not in build_module.CONTRACT_COLUMNS]
    if extra:
        add("warning", f"columns outside the contract: {', '.join(extra)}")

    if not missing:
        units = {str(unit) for unit in frame["unit"].dropna().unique()}
        if units != {spec.output_unit}:
            add("error", f"stored unit {sorted(units)} but the registry says {spec.output_unit!r}")

        for problem in _check_window(frame["timestamp"], spec.start_year, spec.end_year):
            add("error", problem)

        nulls = int(frame["value"].isna().sum())
        if nulls:
            add("warning", f"{nulls} null months")

        if frame["value"].notna().any():
            first, last = frame["timestamp"].iloc[0], frame["timestamp"].iloc[-1]
            # Compare calendar days, not string formats: provenance stores dates,
            # pandas hands back timestamps, and either can carry a time part.
            if not (
                _same_day(entry.get("period_start"), first)
                and _same_day(entry.get("period_end"), last)
            ):
                add(
                    "error",
                    f"provenance period {entry.get('period_start')}..{entry.get('period_end')} "
                    f"does not match the file {first}..{last}",
                )

    box = str(entry.get("requested_box") or "")
    parts = box.split(",")
    if len(parts) != 4:
        add("error", f"requested_box {box!r} is not W,S,E,N")
    else:
        try:
            west, south, east, north = (float(part) for part in parts)
            if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
                add("error", f"requested_box {box!r} is outside valid coordinates")
        except ValueError:
            add("error", f"requested_box {box!r} is not numeric")

    regions = load_regions()
    if region_id not in regions:
        add("error", "region_id is not in pipeline/regions.json")
    elif len(parts) == 4:
        registered = regions[region_id]
        expected = (
            f"{registered['west']},{registered['south']},{registered['east']},{registered['north']}"
        )
        if box and canonical_box(box) != canonical_box(expected):
            add("warning", f"box {box} differs from the registered {expected}")

    if not entry.get("permalink"):
        add("warning", "no permalink (job id was not recorded for this pull)")

    source_name = str(entry.get("source_csv") or "")
    source = raw_root / source_name if source_name else None
    if source is None or not source.exists():
        # data/raw is not committed, so an absent export is unverifiable rather than
        # wrong: the committed series may well be correct and its source simply
        # lives elsewhere (the Giovanni T2M exports are on Kevin's machine).
        add(
            "warning",
            f"the export this series was built from ({source_name!r}) is not in the repo, "
            "so its hash cannot be re-checked",
        )
    else:
        digest = _sha256(source)
        recorded = str(entry.get("source_csv_sha256") or "")
        if not recorded:
            add("error", "provenance has no source hash")
        elif digest != recorded:
            # A file with the recorded name but different bytes is a different pull
            # that happens to share the name, not proof that provenance is wrong.
            add(
                "error",
                f"{source_name} in data/raw is not the export this series was built from "
                "(sha256 differs); restore that export or rebuild the series from this one",
            )

    return issues


def canonical_box(box: str) -> str:
    """Compare boxes as numbers, so '-10.5,51.4,-6,55.4' equals '-10.5,51.4,-6.0,55.4'."""
    try:
        return ",".join(f"{float(part):g}" for part in box.split(","))
    except ValueError:
        return box


def check_dataset(dataset_dir: Path, raw_root: Path) -> list[Issue]:
    """Checks for one dataset folder: provenance shape, registry agreement, every series."""
    issues: list[Issue] = []
    dataset_id = dataset_dir.name
    provenance_path = dataset_dir / "provenance.json"
    if not provenance_path.is_file():
        return [Issue("error", dataset_id, "", "no provenance.json")]

    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [Issue("error", dataset_id, "", f"provenance.json does not parse: {error}")]

    for field_name in REQUIRED_DATASET_FIELDS:
        if not provenance.get(field_name):
            issues.append(Issue("error", dataset_id, "", f"provenance is missing {field_name}"))

    spec = next((v for v in VARIABLES.values() if v.dataset_id == dataset_id), None)
    if spec is None:
        issues.append(Issue("error", dataset_id, "", "dataset_id is not in the registry"))
        return issues

    if canonical_unit(str(provenance.get("output_unit", ""))) != canonical_unit(spec.output_unit):
        issues.append(
            Issue(
                "error",
                dataset_id,
                "",
                f"provenance output_unit {provenance.get('output_unit')!r} != registry "
                f"{spec.output_unit!r}",
            )
        )
    if str(provenance.get("version", "")).lstrip("v") != spec.version.lstrip("v"):
        issues.append(
            Issue(
                "error",
                dataset_id,
                "",
                f"provenance version {provenance.get('version')!r} != registry {spec.version!r}",
            )
        )

    regions = provenance.get("regions") or {}
    if not regions:
        issues.append(Issue("error", dataset_id, "", "provenance lists no regions"))

    on_disk = {path.stem for path in dataset_dir.glob("*.parquet")}
    for region_id in sorted(set(regions) - on_disk):
        issues.append(Issue("error", dataset_id, region_id, "provenance region has no parquet"))
    for region_id in sorted(on_disk - set(regions)):
        issues.append(Issue("error", dataset_id, region_id, "parquet has no provenance entry"))

    for region_id in sorted(set(regions) & on_disk):
        entry = regions[region_id]
        for field_name in REQUIRED_REGION_FIELDS:
            if field_name not in entry:
                issues.append(
                    Issue(
                        "error", dataset_id, region_id, f"region provenance is missing {field_name}"
                    )
                )
        frame = pd.read_parquet(dataset_dir / f"{region_id}.parquet")
        issues.extend(check_series(dataset_id, region_id, frame, entry, spec, raw_root))

    return issues


def regenerate(dataset_dir: Path, raw_root: Path, scratch: Path) -> list[Issue]:
    """Rebuild every series from its raw CSV and compare values, units and timestamps."""
    dataset_id = dataset_dir.name
    spec = next((v for v in VARIABLES.values() if v.dataset_id == dataset_id), None)
    if spec is None:
        return [Issue("error", dataset_id, "", "dataset_id is not in the registry")]

    provenance = json.loads((dataset_dir / "provenance.json").read_text(encoding="utf-8"))
    issues: list[Issue] = []
    for region_id, entry in sorted(provenance.get("regions", {}).items()):
        source = raw_root / str(entry.get("source_csv") or "")
        if not source.is_file():
            issues.append(
                Issue(
                    "warning",
                    dataset_id,
                    region_id,
                    "cannot regenerate: the export this series was built from is not in the repo",
                )
            )
            continue
        try:
            build_module.build(
                source,
                dataset_id=dataset_id,
                variable_id=spec.variable_id,
                region_id=region_id,
                product=spec.product,
                version=spec.version,
                native_unit=str(provenance.get("native_unit") or spec.native_unit),
                output_unit=str(provenance.get("output_unit") or spec.output_unit),
                spatial_resolution=spec.spatial_resolution,
                giovanni_variable_id=str(
                    entry.get("giovanni_variable_id") or spec.giovanni_variable_id
                ),
                requested_box=str(entry.get("requested_box") or "") or None,
                analyzable_region=entry.get("analyzable_region") or None,
                permalink=entry.get("permalink") or None,
                access_date=str(provenance.get("access_date") or "1970-01-01"),
                start_year=None,
                end_year=None,
                out_root=scratch,
                access_route=str(provenance.get("access_route") or "unknown"),
                allow_short=True,
            )
        except ValueError as error:
            issues.append(Issue("error", dataset_id, region_id, f"rebuild failed: {error}"))
            continue

        rebuilt = pd.read_parquet(scratch / dataset_id / f"{region_id}.parquet")
        stored = pd.read_parquet(dataset_dir / f"{region_id}.parquet")
        if not rebuilt["value"].equals(stored["value"]):
            issues.append(Issue("error", dataset_id, region_id, "values differ from a rebuild"))
        elif not rebuilt["timestamp"].equals(stored["timestamp"]):
            issues.append(Issue("error", dataset_id, region_id, "timestamps differ from a rebuild"))

    return issues


def run(processed: Path, raw: Path, *, do_regenerate: bool = False) -> list[Issue]:
    """All checks over every dataset folder."""
    issues: list[Issue] = []
    for dataset_dir in sorted(path for path in processed.iterdir() if path.is_dir()):
        issues.extend(check_dataset(dataset_dir, raw))
        if do_regenerate:
            with tempfile.TemporaryDirectory() as scratch:
                issues.extend(regenerate(dataset_dir, raw, Path(scratch)))
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QA the processed series against their provenance")
    parser.add_argument("--processed", type=Path, default=Path("data/processed"))
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="rebuild each series from its raw CSV and compare (needs data/raw)",
    )
    args = parser.parse_args(argv)

    issues = run(args.processed, args.raw, do_regenerate=args.regenerate)
    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]

    for issue in issues:
        print(issue)

    datasets = sorted(path.name for path in args.processed.iterdir() if path.is_dir())
    print(
        f"\n{len(datasets)} datasets, {len(errors)} errors, {len(warnings)} warnings"
        + (" (regenerated from raw)" if args.regenerate else "")
    )
    if errors:
        return 2 if args.regenerate else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
