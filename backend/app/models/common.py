"""Shared types for the data and API contract (Linear doc 04).

Every model forbids unknown fields, so a file or response that drifts from the
contract fails validation instead of silently passing through.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# snake_case slugs: amazon_basin, sahel, us_southwest, t2m, ...
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_]*$")]

Fraction = Annotated[float, Field(ge=0.0, le=1.0)]

# "land_model" is an additive value: doc 04 lists reanalysis | satellite, but
# GLDAS is a land model (open contract question on NAS-16).
ProductType = Literal["reanalysis", "land_model", "satellite"]

TrendDirection = Literal["increasing", "decreasing", "no_significant_trend", "withheld"]

Verdict = Literal["significant", "weak_evidence", "no_clear_trend", "not_enough_data"]

SeriesUsed = Literal["value", "anomaly"]

CatalogueStatus = Literal["ready", "coming_soon"]

ErrorCode = Literal[
    "region_not_found",
    "dataset_not_found",
    "invalid_parameter",
    "data_unavailable",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
