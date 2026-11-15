"""Regions, stored as geometry so polygons can replace boxes later.

Today every POC region is a box, and a box average includes ocean and
neighbouring land by construction. The ``BBox`` object is the seam: a future
``Polygon`` with an area-weighted zonal mean replaces it without changing
``Region``'s public surface.
"""

from __future__ import annotations

import difflib
import json
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import cache
from ._registry import VARIABLES

_RESOLUTION_NUMBERS = re.compile(r"\d+(?:\.\d+)?")

#: Minimum number of native cells a box should cover before its mean is
#: treated as a regional average rather than a point sample.
MIN_CELLS = 4


class UnknownRegionError(KeyError):
    """Raised for a misspelled or unknown region id."""


@dataclass(frozen=True)
class BBox:
    """A west/south/east/north box in degrees."""

    west: float
    south: float
    east: float
    north: float

    @property
    def width(self) -> float:
        return self.east - self.west

    @property
    def height(self) -> float:
        return self.north - self.south

    @property
    def area_km2(self) -> float:
        """Rough area; good enough to say 'this is a small box', not for science."""
        mid_latitude = math.radians((self.south + self.north) / 2.0)
        return self.width * 111.32 * math.cos(mid_latitude) * self.height * 110.57

    def to_geojson(self) -> dict[str, Any]:
        """A GeoJSON Feature with a closed polygon ring."""
        ring = [
            [self.west, self.south],
            [self.east, self.south],
            [self.east, self.north],
            [self.west, self.north],
            [self.west, self.south],
        ]
        return {
            "type": "Feature",
            "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        }


@dataclass(frozen=True)
class CellCoverage:
    """How many native grid cells a region covers for one variable."""

    cells: int
    lat_resolution: float
    lon_resolution: float
    warn: bool
    detail: str


def parse_resolution(text: str) -> tuple[float, float]:
    """Parse the registry's resolution strings into ``(lat, lon)`` degrees.

    Handles ``"0.25°"``, ``"0.1°"`` and MERRA-2's ``"0.5° x 0.625°"``, which is
    latitude x longitude in the registry.
    """
    numbers = [float(value) for value in _RESOLUTION_NUMBERS.findall(text)]
    if not numbers:
        raise ValueError(f"cannot read a grid resolution from {text!r}")
    if len(numbers) == 1:
        return numbers[0], numbers[0]
    return numbers[0], numbers[1]


_REGIONS_PATH = Path(__file__).resolve().parent / "_data" / "regions.json"


@lru_cache(maxsize=1)
def _raw_regions() -> dict[str, dict[str, Any]]:
    """Region metadata bundled with the package."""
    payload = json.loads(_REGIONS_PATH.read_text(encoding="utf-8"))
    return {region["region_id"]: region for region in payload["regions"]}


def region_ids() -> list[str]:
    """The five POC regions (entries scoped to every variable)."""
    return sorted(
        region_id
        for region_id, payload in _raw_regions().items()
        if payload.get("scope", "all") == "all"
    )


def get_region(region_id: str) -> Region:
    """Return one region, or raise an error that suggests the closest id."""
    known = region_ids()
    if region_id not in known:
        close = difflib.get_close_matches(region_id, known, n=1)
        hint = f" Did you mean {close[0]!r}?" if close else ""
        raise UnknownRegionError(
            f"unknown region {region_id!r}.{hint} Known regions: {', '.join(known)}"
        )
    return Region(_raw_regions()[region_id])


class Region:
    """One place, its geometry, and the variables it has data for."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.region_id: str = payload["region_id"]
        self.name: str = payload.get("name", self.region_id)
        self.scope: str = payload.get("scope", "all")
        self.bbox = BBox(
            west=float(payload["west"]),
            south=float(payload["south"]),
            east=float(payload["east"]),
            north=float(payload["north"]),
        )

    # -- variables ----------------------------------------------------------
    @property
    def variables(self) -> dict[str, bool]:
        """Alias -> whether a processed series exists for this region."""
        from .variables import VARIABLE_CLASSES

        available: dict[str, bool] = {}
        for alias, cls in VARIABLE_CLASSES.items():
            spec = VARIABLES[cls.variable_id]
            available[alias] = cache.has_series(spec.dataset_id, self.region_id)
        return available

    def available_variables(self) -> list[str]:
        return [alias for alias, present in self.variables.items() if present]

    def __getattr__(self, alias: str) -> Any:
        from .variables import VARIABLE_CLASSES

        if alias in VARIABLE_CLASSES:
            return VARIABLE_CLASSES[alias](self)
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {alias!r}")

    # -- geometry -----------------------------------------------------------
    def cells(self, variable_id: str) -> CellCoverage:
        """Estimate the native cells inside the box for one variable."""
        spec = VARIABLES[variable_id]
        lat_resolution, lon_resolution = parse_resolution(spec.spatial_resolution)
        lon_cells = max(1, round(self.bbox.width / lon_resolution))
        lat_cells = max(1, round(self.bbox.height / lat_resolution))
        cells = lon_cells * lat_cells
        too_narrow = self.bbox.width < 2 * lon_resolution
        too_short = self.bbox.height < 2 * lat_resolution
        warn = cells < MIN_CELLS or too_narrow or too_short
        detail = (
            f"{cells} cell(s) at {spec.spatial_resolution} (~{lon_cells} across, ~{lat_cells} down)"
        )
        if warn:
            detail += (
                f"; below {MIN_CELLS} cells or under two cell widths, so this is "
                "closer to a point sample than a regional average"
            )
        return CellCoverage(
            cells=cells,
            lat_resolution=lat_resolution,
            lon_resolution=lon_resolution,
            warn=warn,
            detail=detail,
        )

    def to_geojson(self) -> dict[str, Any]:
        feature = self.bbox.to_geojson()
        feature["properties"] = {"region_id": self.region_id, "name": self.name}
        return feature

    # -- narration ----------------------------------------------------------
    def info(self) -> str:
        """A readable summary; reads no parquet and opens no network."""
        lines = [
            f"{self.name} ({self.region_id})",
            f"  box: {self.bbox.west}, {self.bbox.south}, {self.bbox.east}, {self.bbox.north}",
            f"  area: ~{self.bbox.area_km2 / 1000:.0f} thousand km2",
        ]
        present = self.variables
        for alias, cls in _variable_classes().items():
            spec = VARIABLES[cls.variable_id]
            state = "available" if present[alias] else "no data"
            lines.append(
                f"  {alias:<20} {spec.product} | {spec.output_unit} | "
                f"{spec.start_year}-{spec.end_year} | {state}"
            )
        return "\n".join(lines)

    def summary(self):
        """One row per available variable, sorted by absolute change per decade."""
        import pandas as pd

        rows = []
        for alias in self.available_variables():
            trend = getattr(self, alias).trend()
            low, high = trend.confidence_interval_95 or (None, None)
            rows.append(
                {
                    "variable": alias,
                    "dataset": trend.dataset_id,
                    "per_decade": trend.per_decade,
                    "unit": trend.unit,
                    "ci_low": low,
                    "ci_high": high,
                    "p_value": trend.p_value,
                    "direction": trend.direction,
                    "n_obs": trend.n_obs,
                    "period": f"{trend.period[0]}-{trend.period[1]}",
                    "warnings": "; ".join(trend.warnings),
                }
            )
        frame = pd.DataFrame(rows)
        if frame.empty:
            return frame
        frame["_magnitude"] = frame["per_decade"].abs()
        return (
            frame.sort_values("_magnitude", ascending=False, na_position="last")
            .drop(columns="_magnitude")
            .reset_index(drop=True)
        )

    def __repr__(self) -> str:
        return f"Region({self.region_id!r}, {self.bbox.west}..{self.bbox.east})"


def _variable_classes() -> dict[str, type]:
    from .variables import VARIABLE_CLASSES

    return VARIABLE_CLASSES
