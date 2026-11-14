"""data/processed/<dataset_id>/provenance.json: where every number came from."""

import datetime as dt

from pydantic import Field

from app.models.common import ContractModel, Slug


class Provenance(ContractModel):
    dataset_id: Slug
    product: str = Field(min_length=1)
    version: str = Field(min_length=1)
    doi_or_url: str
    access_date: dt.date
    access_route: str  # Earthdata / GES DISC / Giovanni / ...
    variable_field: str  # native field name
    scale_factor: float
    native_unit: str
    output_unit: str
    spatial_resolution: str
    period_start: dt.date
    period_end: dt.date
    qa_rules: list[str]
    region_source: str  # polygon source + licence
    requested_box: str  # W,S,E,N as requested
    analyzable_region: str  # as reported by Giovanni
    giovanni_variable_id: str
    giovanni_permalink: str
    citation: str  # filled from the doc 11 template
    transformations: list[str]
