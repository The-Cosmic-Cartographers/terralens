"""Check a static snapshot (the output of app.export) before it ships.

    PYTHONPATH=backend uv run python -m app.verify_snapshot [folder]

Every file the export writes must exist, validate against the doc 04 models and sit at the
path its own ids say. A snapshot marked SAMPLE, or any file containing the SAMPLE source
string, fails unless --allow-sample is passed. Exit code 0 means clean.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError

from app.models import (
    CatalogueItem,
    CompareResult,
    Health,
    Lineup,
    Metadata,
    Region,
    SeriesResponse,
    TrendResult,
    Windows,
)

SAMPLE_MARKER = "SAMPLE"


def verify(root: Path, allow_sample: bool = False) -> list[str]:
    """Return a list of problems; an empty list means the snapshot is clean."""
    problems: list[str] = []

    def load(relative: str, parse: Any) -> Any:
        path = root / relative
        if not path.is_file():
            problems.append(f"{relative}: file is missing")
            return None
        text = path.read_text(encoding="utf-8")
        if not allow_sample and SAMPLE_MARKER in text:
            problems.append(f"{relative}: contains {SAMPLE_MARKER} data")
        try:
            return parse(json.loads(text))
        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            problems.append(f"{relative}: does not match the contract ({type(error).__name__})")
            return None

    def model(cls: type[BaseModel]) -> Any:
        return lambda payload: cls.model_validate(payload)

    health = load("health.json", model(Health))
    if health is not None and not allow_sample and SAMPLE_MARKER in health.data_version.upper():
        problems.append(f"health.json: data_version is '{health.data_version}'")
    catalogue = load("catalogue.json", TypeAdapter(list[CatalogueItem]).validate_python)
    regions = load("regions.json", TypeAdapter(list[Region]).validate_python)
    if catalogue is None or regions is None:
        return problems

    for item in (c for c in catalogue if c.status == "ready"):
        dataset = item.dataset_id

        def metadata_ok(m: Metadata, dataset: str = dataset) -> Metadata:
            if m.dataset_id != dataset:
                raise ValueError("wrong dataset")
            return m

        load(f"metadata/{dataset}.json", lambda p, f=metadata_ok: f(Metadata.model_validate(p)))

        def compare_ok(c: CompareResult, dataset: str = dataset) -> CompareResult:
            if c.dataset_id != dataset:
                raise ValueError("wrong dataset")
            return c

        load(f"compare/{dataset}.json", lambda p, f=compare_ok: f(CompareResult.model_validate(p)))
        for region in regions:
            rid = region.region_id
            for kind, cls in (("series", SeriesResponse), ("windows", Windows)):

                def check(payload: Any, cls: Any = cls, dataset: str = dataset, rid: str = rid):
                    obj = cls.model_validate(payload)
                    if (obj.dataset_id, obj.region_id) != (dataset, rid):
                        raise ValueError("wrong dataset or region")
                    return obj

                load(f"{kind}/{dataset}/{rid}.json", check)

            def check_trend(payload: Any, dataset: str = dataset, rid: str = rid) -> TrendResult:
                obj = TrendResult.model_validate(payload)
                if (obj.dataset_id, obj.region_id) != (dataset, rid):
                    raise ValueError("wrong dataset or region")
                return obj

            load(f"trend/{dataset}/{rid}.json", check_trend)

    for region in regions:
        rid = region.region_id

        def check_lineup(payload: Any, rid: str = rid) -> Lineup:
            obj = Lineup.model_validate(payload)
            if obj.region_id != rid:
                raise ValueError("wrong region")
            return obj

        load(f"lineup/{rid}.json", check_lineup)
    return problems


def main(argv: list[str] | None = None) -> int:
    default = Path(__file__).resolve().parents[2] / "frontend" / "public" / "data"
    parser = argparse.ArgumentParser(description="Verify a static snapshot before it ships.")
    parser.add_argument("folder", nargs="?", type=Path, default=default)
    parser.add_argument("--allow-sample", action="store_true", help="development snapshots only")
    args = parser.parse_args(argv)
    problems = verify(args.folder, args.allow_sample)
    if problems:
        print(f"snapshot is NOT clean ({len(problems)} problems):", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(f"snapshot at {args.folder} is clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
