"""data/processed/<dataset_id>/provenance.json: where every number came from.

One file per dataset. Fields about the product are at the top level; fields that differ
per region (the box asked for, the region Giovanni analysed, the permalink, the source
CSV) live in `regions`, so adding a region does not rewrite the file.
"""

import datetime as dt
from typing import Self

from pydantic import Field, model_validator

from app.models.common import ContractModel, Slug


class RegionProvenance(ContractModel):
    region_id: Slug
    requested_box: str  # W,S,E,N as requested
    analyzable_region: str  # as reported by Giovanni ("" until recorded)
    giovanni_variable_id: str
    permalink: str  # the Giovanni permalink of this series
    period_start: dt.date
    period_end: dt.date
    source_csv: str
    source_csv_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observations: int = Field(ge=0)
    transformations: list[str]


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
    period_start: dt.date  # of the most recent run
    period_end: dt.date
    qa_rules: list[str]
    region_source: str  # polygon source + licence
    citation: str = ""  # filled from the doc 11 template before submission (NAS-43)
    transformations: list[str]
    regions: dict[Slug, RegionProvenance] = Field(min_length=1)

    @model_validator(mode="after")
    def check_regions(self) -> Self:
        for key, region in self.regions.items():
            if key != region.region_id:
                raise ValueError("every regions key must equal its region_id")
        return self
