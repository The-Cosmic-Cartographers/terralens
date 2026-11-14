"""Pydantic models for the data and API contract (Linear doc 04)."""

from app.models.meta import CatalogueItem, ErrorBody, ErrorResponse, Health, Metadata, Region
from app.models.provenance import Provenance, RegionProvenance
from app.models.results import (
    ChangePoint,
    CompareResult,
    Lineup,
    LineupRow,
    SeasonalSlopes,
    TrendResult,
    Window,
    Windows,
)
from app.models.series import SeriesResponse, SeriesRow

__all__ = [
    "CatalogueItem",
    "ChangePoint",
    "CompareResult",
    "ErrorBody",
    "ErrorResponse",
    "Health",
    "Lineup",
    "LineupRow",
    "Metadata",
    "Provenance",
    "Region",
    "RegionProvenance",
    "SeasonalSlopes",
    "SeriesResponse",
    "SeriesRow",
    "TrendResult",
    "Window",
    "Windows",
]
