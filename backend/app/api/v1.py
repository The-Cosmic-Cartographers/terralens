"""REST API v1, part A: catalogue, regions and metadata (doc 04 §3)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.config import data_dir
from app.models import CatalogueItem, ErrorResponse, Metadata, Region
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


def get_store() -> DataStore:
    # Resolved per request so TERRALENS_DATA_DIR can point at data/ or data/fixtures.
    return DataStore(data_dir())


Store = Annotated[DataStore, Depends(get_store)]
DatasetId = Annotated[str, Query(pattern=r"^[a-z0-9][a-z0-9_]*$", description="Dataset slug")]


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
