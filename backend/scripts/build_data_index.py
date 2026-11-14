"""Write the index files for the real data folder: catalogue, regions, metadata, data_version.

The pipeline writes `data/processed/<dataset_id>/<region_id>.parquet` and a provenance.json.
This reads those, plus the registry in `pipeline/`, and writes what the API also needs:

    data/catalogue.json            one entry per Lineup row; `ready` once its series exist
    data/regions.json              the regions that have at least one processed series
    data/metadata/<dataset_id>.json
    data/data_version.txt          "giovanni-<newest access date>"

    PYTHONPATH=backend:. uv run python -m scripts.build_data_index

Nothing here is a statistic. Re-run it after every pipeline run; the output is deterministic.
"""

import argparse
import datetime as dt
import json
from pathlib import Path

from app.models import CatalogueItem, Metadata, Provenance, Region
from pipeline.regions import APP_REGIONS, load_regions
from pipeline.registry import VARIABLES

LABELS = {
    "t2m": "Air temperature (2 m)",
    "soil_moisture_0_10": "Soil moisture (0-10 cm)",
    "evapotranspiration": "Evapotranspiration",
    "precipitation": "Precipitation",
    "aerosol": "Aerosol optical depth",
    "no2": "NO2 column (troposphere)",
}

LIMITATIONS = [
    "Each value is an average over the region's box, so it hides what happens inside the box.",
    "Giovanni snaps the requested box to the product's grid; the region it actually analysed is "
    "recorded in the provenance.",
    "MERRA-2 is a model reconstruction constrained by observations, not a direct measurement. "
    "Changes in what it assimilates can create artificial steps in a record.",
    "Months with no value are kept as empty rows, never filled in.",
]
REGION_SOURCE = "Region boxes defined by TerraLens (Linear doc 01, decision D19)"
REGION_LICENCE = "TerraLens project boxes; no third-party boundary data"


def box_polygon(box: dict) -> dict:
    w, s, e, n = box["west"], box["south"], box["east"], box["north"]
    return {"type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]}


def build(processed: Path, out: Path) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    (out / "metadata").mkdir(exist_ok=True)
    boxes = load_regions()
    unknown = [r for r in APP_REGIONS if r not in boxes]
    if unknown:
        raise ValueError(f"APP_REGIONS not in pipeline/regions.json: {', '.join(unknown)}")
    ids = [spec.dataset_id for spec in VARIABLES.values()]
    if len(set(ids)) != len(ids):
        raise ValueError(
            "two variables share a dataset_id; their series would overwrite each other"
        )

    catalogue: list[CatalogueItem] = []
    newest = dt.date.min
    written: list[str] = []

    for spec in VARIABLES.values():
        folder = processed / spec.dataset_id
        provenance_file = folder / "provenance.json"
        files = sorted(folder.glob("*.parquet")) if folder.is_dir() else []
        covered = {path.stem for path in files}
        if not set(APP_REGIONS) <= covered or not provenance_file.is_file():
            catalogue.append(
                CatalogueItem(
                    dataset_id=spec.dataset_id,
                    variable_id=spec.variable_id,
                    label=LABELS[spec.variable_id],
                    unit=spec.output_unit,
                    period_start=dt.date(spec.start_year, 1, 1),
                    period_end=dt.date(spec.end_year, 12, 1),
                    status="coming_soon",
                )
            )
            continue
        provenance = Provenance(**json.loads(provenance_file.read_text(encoding="utf-8")))
        newest = max(newest, provenance.access_date)
        catalogue.append(
            CatalogueItem(
                dataset_id=spec.dataset_id,
                variable_id=spec.variable_id,
                label=LABELS[spec.variable_id],
                unit=provenance.output_unit,
                period_start=min(provenance.regions[r].period_start for r in APP_REGIONS),
                period_end=max(provenance.regions[r].period_end for r in APP_REGIONS),
                status="ready",
            )
        )
        extras = {
            "methodology": (
                f"{provenance.product}, version {provenance.version}, accessed through "
                f"{provenance.access_route} as an area-averaged monthly time series, "
                f"converted from {provenance.native_unit} to {provenance.output_unit}. "
                "Whole calendar years only. "
                "Trends are computed afterwards by the analysis module (seasonal Mann-Kendall "
                "with Sen's slope); this file describes the data only."
            ),
            "limitations": LIMITATIONS,
            "attribution": (
                f"{provenance.product}. NASA Goddard Earth Sciences Data and Information Services "
                f"Center (GES DISC), accessed through {provenance.access_route} on "
                f"{provenance.access_date.isoformat()}."
            ),
        }
        Metadata(dataset_id=spec.dataset_id, provenance=provenance, **extras)  # must validate
        target = out / "metadata" / f"{spec.dataset_id}.json"
        # The API adds dataset_id and the provenance; the file holds only the three text fields.
        target.write_text(json.dumps(extras, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(f"metadata/{spec.dataset_id}.json")

    regions = []
    for region_id in APP_REGIONS:
        box = boxes[region_id]
        regions.append(
            Region(
                region_id=region_id,
                name=box["name"],
                description=(
                    f"Box {box['west']} to {box['east']} degrees east, "
                    f"{box['south']} to {box['north']} degrees north."
                ),
                geometry=box_polygon(box),
                source=REGION_SOURCE,
                licence=REGION_LICENCE,
            )
        )
    (out / "catalogue.json").write_text(
        json.dumps([c.model_dump(mode="json") for c in catalogue], indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    (out / "regions.json").write_text(
        json.dumps([r.model_dump(mode="json") for r in regions], indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    (out / "data_version.txt").write_text(f"giovanni-{newest.isoformat()}\n", encoding="utf-8")
    return ["catalogue.json", "regions.json", "data_version.txt", *written]


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--processed", type=Path, default=root / "data" / "processed")
    parser.add_argument("--out", type=Path, default=root / "data")
    args = parser.parse_args(argv)
    print("wrote " + ", ".join(build(args.processed, args.out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
