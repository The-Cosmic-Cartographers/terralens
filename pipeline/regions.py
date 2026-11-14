"""Region boxes for the Lineup, loaded from ``pipeline/regions.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REGIONS_PATH = Path(__file__).with_name("regions.json")


def load_regions(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """Return every region keyed by ``region_id``."""
    source = Path(path) if path is not None else REGIONS_PATH
    payload = json.loads(source.read_text(encoding="utf-8"))
    return {region["region_id"]: region for region in payload["regions"]}


def get_region(region_id: str, path: str | Path | None = None) -> dict[str, Any]:
    """Return one region, raising a readable error when the id is unknown."""
    regions = load_regions(path)
    try:
        return regions[region_id]
    except KeyError:
        known = ", ".join(sorted(regions))
        raise KeyError(f"unknown region_id {region_id!r}; known ids: {known}") from None


def box_string(region: dict[str, Any]) -> str:
    """Format a region box as W,S,E,N for a Giovanni request."""
    return f"{region['west']},{region['south']},{region['east']},{region['north']}"
