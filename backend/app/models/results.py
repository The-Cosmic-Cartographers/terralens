"""Schemas 2, 2a and 2b: statistical results (analysis -> backend).

The contract's rules are enforced here so a result that breaks them (a withheld
trend that still carries statistics, a "significant" verdict on an adjusted
p-value above 0.05, ...) cannot reach the API or the static export.
"""

import datetime as dt
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from app.models.common import (
    ContractModel,
    Fraction,
    ProductType,
    SeriesUsed,
    Slug,
    TrendDirection,
    Verdict,
)

SIGNIFICANCE_LEVEL = 0.05  # the "0_05" in significant_at_0_05

BhFamily = Annotated[str, StringConstraints(pattern=r"^(lineup|compare):[a-z0-9_]+$")]
ConfidenceInterval = tuple[float, float]


class TrendResult(ContractModel):
    """data/results/<dataset_id>/trends.json holds a list of these, one per region."""

    dataset_id: Slug
    variable_id: Slug
    region_id: Slug
    period_start: dt.date
    period_end: dt.date
    series_used: SeriesUsed
    trend_direction: TrendDirection
    sen_slope_per_year: float | None
    unit_per_year: str
    confidence_interval_95: ConfidenceInterval | None
    p_value: Fraction | None
    adjusted_p_value: Fraction | None
    adjustment_method: Literal["benjamini_hochberg"]
    significant_at_0_05: bool
    observation_count: int = Field(ge=0)
    missing_month_count: int = Field(ge=0)
    mean_coverage_fraction: Fraction
    method: str
    serial_correlation_note: str
    caveats: list[str]
    withheld_reason: str | None
    product_type: ProductType
    bh_family: BhFamily
    verdict: Verdict
    effect_size_swings: float | None  # change over the window / s.d. of annual-mean anomalies
    detect_years: float | None = Field(default=None, ge=0)  # only for non-significant verdicts

    @model_validator(mode="after")
    def check_contract_rules(self) -> Self:
        if self.period_end < self.period_start:
            raise ValueError("period_end cannot be before period_start")

        statistics = (
            self.sen_slope_per_year,
            self.confidence_interval_95,
            self.p_value,
            self.adjusted_p_value,
        )

        if self.trend_direction == "withheld":
            # Doc 04 §2: null out the statistics and fill in withheld_reason.
            if any(s is not None for s in statistics):
                raise ValueError("a withheld result must have null statistics")
            if self.effect_size_swings is not None or self.detect_years is not None:
                raise ValueError("a withheld result must not carry effect size or detectability")
            if not self.withheld_reason:
                raise ValueError("a withheld result needs a withheld_reason")
            if self.verdict != "not_enough_data":
                raise ValueError("a withheld result must have the verdict not_enough_data")
            if self.significant_at_0_05:
                raise ValueError("a withheld result cannot be significant")
            return self

        if any(s is None for s in statistics):
            raise ValueError("a result that is not withheld needs slope, CI, p and adjusted p")
        if self.withheld_reason is not None:
            raise ValueError("withheld_reason is only for withheld results")
        if self.verdict == "not_enough_data":
            raise ValueError("verdict not_enough_data is only for withheld results")

        assert self.sen_slope_per_year is not None
        assert self.confidence_interval_95 is not None
        assert self.p_value is not None
        assert self.adjusted_p_value is not None

        low, high = self.confidence_interval_95
        if low > high:
            raise ValueError("confidence_interval_95 must be ordered [low, high]")
        if self.adjusted_p_value < self.p_value - 1e-9:
            raise ValueError("an adjusted p-value cannot be below the raw p-value")

        significant = self.adjusted_p_value < SIGNIFICANCE_LEVEL
        if self.significant_at_0_05 != significant:
            raise ValueError("significant_at_0_05 must match adjusted_p_value < 0.05")
        if (self.verdict == "significant") != significant:
            raise ValueError("the verdict is 'significant' exactly when adjusted p < 0.05")

        if significant:
            if self.trend_direction not in ("increasing", "decreasing"):
                raise ValueError("a significant trend must be increasing or decreasing")
            if self.trend_direction == "increasing" and self.sen_slope_per_year <= 0:
                raise ValueError("an increasing trend needs a positive slope")
            if self.trend_direction == "decreasing" and self.sen_slope_per_year >= 0:
                raise ValueError("a decreasing trend needs a negative slope")
            if self.detect_years is not None:
                raise ValueError("detect_years is only for non-significant verdicts")
        elif self.trend_direction != "no_significant_trend":
            raise ValueError("a non-significant result must have no_significant_trend")
        return self


class LineupRow(ContractModel):
    dataset_id: Slug
    variable_id: Slug
    label: str = Field(min_length=1)
    definition: str = Field(min_length=1)  # plain-language one-liner for students
    product_type: ProductType
    period_start: dt.date
    period_end: dt.date
    sparkline: list[float]
    trend: TrendResult

    @model_validator(mode="after")
    def check_row(self) -> Self:
        if (self.trend.dataset_id, self.trend.variable_id) != (self.dataset_id, self.variable_id):
            raise ValueError("the row's trend must belong to the row's dataset and variable")
        if self.trend.product_type != self.product_type:
            raise ValueError("the row's product_type must match its trend's product_type")
        return self


class Lineup(ContractModel):
    """data/results/lineup/<region_id>.json: the ranked board for one place."""

    region_id: Slug
    bh_family: BhFamily
    rows: list[LineupRow] = Field(min_length=1)

    @model_validator(mode="after")
    def check_family(self) -> Self:
        if self.bh_family != f"lineup:{self.region_id}":
            raise ValueError("a lineup's bh_family must be lineup:<region_id>")
        for row in self.rows:
            if row.trend.region_id != self.region_id:
                raise ValueError("every row must belong to the lineup's region")
            if row.trend.bh_family != self.bh_family:
                raise ValueError("every row's trend must use the lineup's BH family")
        return self


class Window(ContractModel):
    """One Time Machine window (whole calendar years, inclusive)."""

    start: int = Field(ge=1900, le=2100)
    end: int = Field(ge=1900, le=2100)
    sen_slope_per_year: float | None
    confidence_interval_95: ConfidenceInterval | None
    p_value: Fraction | None
    adjusted_p_value: Fraction | None
    verdict: Verdict

    @model_validator(mode="after")
    def check_window(self) -> Self:
        if self.end < self.start:
            raise ValueError("a window's end year cannot be before its start year")
        statistics = (
            self.sen_slope_per_year,
            self.confidence_interval_95,
            self.p_value,
            self.adjusted_p_value,
        )
        if self.verdict == "not_enough_data":
            if any(s is not None for s in statistics):
                raise ValueError("a not_enough_data window must have null statistics")
        elif any(s is None for s in statistics):
            raise ValueError("a window with a verdict needs slope, CI, p and adjusted p")
        return self


class Windows(ContractModel):
    """data/results/windows/<dataset_id>/<region_id>.json."""

    dataset_id: Slug
    region_id: Slug
    min_window_years: int = Field(ge=1)
    windows: list[Window]

    @model_validator(mode="after")
    def check_lengths(self) -> Self:
        for window in self.windows:
            if window.end - window.start + 1 < self.min_window_years:
                raise ValueError("every window must span at least min_window_years")
        return self


class CompareResult(ContractModel):
    """GET /api/v1/compare: every region's result for one variable on a common period."""

    dataset_id: Slug
    variable_id: Slug
    period_start: dt.date
    period_end: dt.date
    period_note: str | None = None  # required reading when periods differ
    bh_family: BhFamily
    results: list[TrendResult] = Field(min_length=1)

    @model_validator(mode="after")
    def check_family(self) -> Self:
        if self.bh_family != f"compare:{self.variable_id}":
            raise ValueError("a compare result's bh_family must be compare:<variable_id>")
        for result in self.results:
            if (result.dataset_id, result.variable_id) != (self.dataset_id, self.variable_id):
                raise ValueError("every result must belong to the compare dataset and variable")
            if result.bh_family != self.bh_family:
                raise ValueError("every result must use the compare BH family")
        return self
