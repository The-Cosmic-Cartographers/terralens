"""Schema 1: processed regional time series (pipeline -> analysis, backend)."""

import datetime as dt
import math
from typing import Self

from pydantic import Field, model_validator

from app.models.common import ContractModel, Fraction, Slug


class SeriesRow(ContractModel):
    """One row per month in data/processed/<dataset_id>/<region_id>.parquet."""

    dataset_id: Slug
    variable_id: Slug
    region_id: Slug
    timestamp: dt.date
    value: float | None  # area-weighted regional value; null if withheld
    unit: str = Field(min_length=1)  # verified from product metadata, after scale factors
    anomaly: float | None = None  # value minus climatology, if the baseline is approved
    valid_cell_count: int = Field(ge=0)
    total_cell_count: int = Field(gt=0)
    coverage_fraction: Fraction
    n_valid_days: int | None = Field(default=None, ge=0)  # daily products only (OMI NO2)
    quality_summary: str
    source: str = Field(min_length=1)  # product identifier and version

    @model_validator(mode="after")
    def check_row(self) -> Self:
        if self.timestamp.day != 1:
            raise ValueError("timestamp must be the first day of the month")
        if self.valid_cell_count > self.total_cell_count:
            raise ValueError("valid_cell_count cannot exceed total_cell_count")
        expected = self.valid_cell_count / self.total_cell_count
        if not math.isclose(self.coverage_fraction, expected, abs_tol=0.005):
            raise ValueError("coverage_fraction must equal valid_cell_count / total_cell_count")
        return self


class SeriesResponse(ContractModel):
    """GET /api/v1/regions/{region_id}/series: rows plus a unit summary."""

    dataset_id: Slug
    variable_id: Slug
    region_id: Slug
    unit: str = Field(min_length=1)
    rows: list[SeriesRow]

    @model_validator(mode="after")
    def check_rows(self) -> Self:
        for row in self.rows:
            if (row.dataset_id, row.variable_id, row.region_id) != (
                self.dataset_id,
                self.variable_id,
                self.region_id,
            ):
                raise ValueError(
                    "every row must belong to the response's dataset, variable and region"
                )
            if row.unit != self.unit:
                raise ValueError("every row's unit must match the response unit")
        return self
