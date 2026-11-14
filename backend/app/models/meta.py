"""Catalogue, regions, metadata, health and error shapes (doc 04 §3)."""

import datetime as dt
from typing import Any, Literal, Self

from pydantic import Field, model_validator

from app.models.common import CatalogueStatus, ContractModel, ErrorCode, Slug
from app.models.provenance import Provenance


class CatalogueItem(ContractModel):
    """GET /api/v1/catalogue returns a list of these."""

    dataset_id: Slug
    variable_id: Slug
    label: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    period_start: dt.date
    period_end: dt.date
    status: CatalogueStatus


class Region(ContractModel):
    """GET /api/v1/regions returns a list of these."""

    region_id: Slug
    name: str = Field(min_length=1)
    description: str
    geometry: dict[str, Any] | None = None  # GeoJSON geometry
    geometry_url: str | None = None  # or a URL to it
    source: str = Field(min_length=1)
    licence: str = Field(min_length=1)

    @model_validator(mode="after")
    def check_geometry(self) -> Self:
        if self.geometry is None and self.geometry_url is None:
            raise ValueError("a region needs a geometry or a geometry_url")
        return self


class Metadata(ContractModel):
    """GET /api/v1/metadata?dataset_id=: provenance, method, limitations, attribution."""

    dataset_id: Slug
    provenance: Provenance
    methodology: str
    limitations: list[str]
    attribution: str

    @model_validator(mode="after")
    def check_dataset(self) -> Self:
        if self.provenance.dataset_id != self.dataset_id:
            raise ValueError("the provenance must belong to the metadata's dataset")
        return self


class Health(ContractModel):
    status: Literal["ok"]
    data_version: str


class ErrorBody(ContractModel):
    code: ErrorCode
    message: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(ContractModel):
    error: ErrorBody
