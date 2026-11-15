"""A synthetic series with a known slope, and the five-variable matrix."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import terralens as tl
from terralens import _registry as registry
from terralens.regions import CellCoverage, Region
from terralens.variables import VARIABLE_CLASSES


def _synthetic_frame(
    slope_per_year: float, years: int = 30, noise: float = 0.6, seed: int = 42
) -> pd.DataFrame:
    """A seasonal series with a known trend and realistic residuals.

    Noise is not decoration: with a noiseless ramp the lag-1 autocorrelation is
    ~0.99 and Hamed-Rao inflates the variance by ~199, so every slope lands at
    the same p. Real series carry residuals.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("1991-01-01", periods=years * 12, freq="MS")
    elapsed = np.arange(len(dates)) / 12.0
    seasonal = 3.0 * np.sin(2 * np.pi * (dates.month - 1) / 12.0)
    return pd.DataFrame(
        {
            "date": dates,
            "value": 20.0 + slope_per_year * elapsed + seasonal + rng.normal(0, noise, len(dates)),
            "coverage_fraction": 1.0,
        }
    )


def test_a_known_slope_is_recovered(monkeypatch):
    from terralens.variables import Temperature

    monkeypatch.setattr(Temperature, "load", lambda self: _synthetic_frame(0.05))
    result = tl.ireland.temperature.trend()

    assert result.per_decade == pytest.approx(0.5, abs=0.15)
    assert result.p_value is not None and result.p_value < 0.01
    assert result.direction == "increasing"


def test_a_flat_series_is_not_significant(monkeypatch):
    from terralens.variables import Temperature

    monkeypatch.setattr(Temperature, "load", lambda self: _synthetic_frame(0.0))
    result = tl.ireland.temperature.trend()

    assert result.p_value is not None and result.p_value > 0.05
    assert result.direction == "no_significant_trend"


@pytest.mark.parametrize(
    "alias", ["soil_moisture", "evapotranspiration", "precipitation", "aerosol"]
)
@pytest.mark.parametrize("region_id", ["ireland", "sahel"])
def test_each_remaining_variable_trends(alias, region_id):
    variable = getattr(tl.region(region_id), alias)
    trend = variable.trend()

    spec = registry.VARIABLES[VARIABLE_CLASSES[alias].variable_id]
    assert trend.unit == spec.output_unit
    assert trend.period == (spec.start_year, spec.end_year)
    assert trend.per_decade is not None
    assert len(variable.load()) > 200


def test_a_small_region_warning_reaches_the_result(monkeypatch):
    def tiny(_self, _variable_id):
        return CellCoverage(
            cells=1,
            lat_resolution=0.5,
            lon_resolution=0.625,
            warn=True,
            detail="1 cell at 0.5° x 0.625°",
        )

    monkeypatch.setattr(Region, "cells", tiny)
    result = tl.ireland.temperature.trend()

    assert any("region resolution" in warning for warning in result.warnings)


def test_refresh_points_at_the_pull_command():
    with pytest.raises(NotImplementedError) as caught:
        tl.ireland.temperature.refresh()
    assert "pipeline.pull" in str(caught.value)
