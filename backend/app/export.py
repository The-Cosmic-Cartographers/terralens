"""Static export: write every API response as a JSON file (doc 04 §5).

The deployed app reads these files, so it needs no live server. The export uses
the same DataStore as the API, so the files cannot drift from the API shapes.

    PYTHONPATH=backend uv run python -m app.export

    data_dir/ ---> frontend/public/data/
        health.json                       data_version (drives the SAMPLE banner)
        catalogue.json, regions.json
        metadata/<dataset_id>.json
        lineup/<region_id>.json
        series|trend|windows/<dataset_id>/<region_id>.json

(compare/<dataset_id>.json arrives with NAS-23.)
"""

import argparse
import json
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import data_dir
from app.models import Health
from app.services.store import DataStore, DataUnavailable

# Only these names are ever removed from the output folder.
GENERATED = (
    "health.json",
    "catalogue.json",
    "regions.json",
    "metadata",
    "lineup",
    "series",
    "trend",
    "windows",
)


class ExportError(Exception):
    """The export would ship something wrong; nothing was written."""


def dump(payload: BaseModel | list[BaseModel]) -> str:
    if isinstance(payload, list):
        data: Any = [item.model_dump(mode="json") for item in payload]
    else:
        data = payload.model_dump(mode="json")
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"


def build_files(store: DataStore, allow_sample: bool) -> dict[Path, str]:
    version = store.data_version()
    if "SAMPLE" in version.upper() and not allow_sample:
        raise ExportError(
            f"The data is marked '{version}'. SAMPLE data must not reach the deployed demo. "
            "Pass --allow-sample to export it for local development."
        )

    catalogue = store.catalogue()
    regions = store.regions()
    files: dict[Path, str] = {
        Path("health.json"): dump(Health(status="ok", data_version=version)),
        Path("catalogue.json"): dump(catalogue),
        Path("regions.json"): dump(regions),
    }
    failures: list[str] = []

    def add(path: Path, read: Callable[[], BaseModel]) -> None:
        try:
            files[path] = dump(read())
        except DataUnavailable as error:
            failures.append(f"{path}: {error}")

    for item in (c for c in catalogue if c.status == "ready"):
        add(
            Path("metadata") / f"{item.dataset_id}.json",
            lambda i=item: store.metadata(i.dataset_id),
        )
        for region in regions:
            name = Path(item.dataset_id) / f"{region.region_id}.json"
            ids = (region.region_id, item.dataset_id)
            add(Path("series") / name, lambda ids=ids: store.series(*ids))
            add(Path("trend") / name, lambda ids=ids: store.trend(*ids))
            add(Path("windows") / name, lambda ids=ids: store.windows(*ids))
    for region in regions:
        add(Path("lineup") / f"{region.region_id}.json", lambda r=region: store.lineup(r.region_id))

    if failures:
        raise ExportError(
            "Refusing to export a snapshot with holes. Missing or invalid:\n  "
            + "\n  ".join(failures)
        )
    return files


def export(root: Path, out: Path, allow_sample: bool = False) -> list[Path]:
    """Write the snapshot to `out`; returns the files written (relative paths)."""
    files = build_files(DataStore(root), allow_sample)  # nothing is touched if this fails

    out.mkdir(parents=True, exist_ok=True)
    for name in GENERATED:
        target = out / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    for relative, text in files.items():
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return sorted(files)


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Write the static JSON snapshot.")
    parser.add_argument(
        "--data-dir", type=Path, default=data_dir(), help="data root (default ./data)"
    )
    parser.add_argument(
        "--out", type=Path, default=repo_root / "frontend" / "public" / "data", help="output folder"
    )
    parser.add_argument(
        "--allow-sample", action="store_true", help="allow SAMPLE data (local development only)"
    )
    args = parser.parse_args(argv)
    try:
        written = export(args.data_dir, args.out, args.allow_sample)
    except (ExportError, DataUnavailable) as error:
        print(f"export failed: {error}", file=sys.stderr)
        return 1
    version = DataStore(args.data_dir).data_version()
    print(f"wrote {len(written)} files to {args.out} (data_version: {version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
