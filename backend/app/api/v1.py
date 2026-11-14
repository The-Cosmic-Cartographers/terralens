"""REST API v1 (doc 04 §3): catalogue, regions, metadata, series, trend, lineup, windows."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.config import data_dir
from app.models import (
    CatalogueItem,
    ErrorResponse,
    Lineup,
    Metadata,
    Region,
    SeriesResponse,
    TrendResult,
    Windows,
)
from app.services.store import DataStore

router = APIRouter(
    prefix="/api/v1",
    tags=["v1"],
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)

SLUG = r"^[a-z0-9][a-z0-9_]*$"


def get_store() -> DataStore:
    # Resolved per request so TERRALENS_DATA_DIR can point at data/ or data/fixtures.
    return DataStore(data_dir())


Store = Annotated[DataStore, Depends(get_store)]
DatasetId = Annotated[str, Query(pattern=SLUG, description="Dataset slug")]
RegionId = Annotated[str, Path(pattern=SLUG, description="Region slug")]


@router.get("/catalogue", response_model=list[CatalogueItem])
def catalogue(store: Store) -> list[CatalogueItem]:
    """Available variables and datasets; `coming_soon` ones are listed but not ready."""
    return store.catalogue()


@router.get("/regions", response_model=list[Region])
def regions(store: Store) -> list[Region]:
    """Regions with their GeoJSON geometry (or a URL to it) and source/licence."""
    return store.regions()


@router.get("/metadata", response_model=Metadata)
def metadata(dataset_id: DatasetId, store: Store) -> Metadata:
    """Provenance, methodology, limitations and attribution for one dataset."""
    return store.metadata(dataset_id)


@router.get("/regions/{region_id}/series", response_model=SeriesResponse)
def series(region_id: RegionId, dataset_id: DatasetId, store: Store) -> SeriesResponse:
    """Monthly series rows (schema 1) plus a unit summary."""
    return store.series(region_id, dataset_id)


@router.get("/regions/{region_id}/trend", response_model=TrendResult)
def trend(region_id: RegionId, dataset_id: DatasetId, store: Store) -> TrendResult:
    """The trend result (schema 2). A withheld result is 200 with `trend_direction: withheld`."""
    return store.trend(region_id, dataset_id)


@router.get("/regions/{region_id}/lineup", response_model=Lineup)
def lineup(region_id: RegionId, store: Store) -> Lineup:
    """The ranked board for one region (schema 2a)."""
    return store.lineup(region_id)


@router.get("/regions/{region_id}/windows", response_model=Windows)
def windows(region_id: RegionId, dataset_id: DatasetId, store: Store) -> Windows:
    """Time Machine windows for one region and dataset (schema 2b)."""
    return store.windows(region_id, dataset_id)
