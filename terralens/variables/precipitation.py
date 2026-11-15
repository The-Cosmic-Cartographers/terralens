"""Precipitation (GPM IMERG Final, V07B), reported in mm/month."""

from __future__ import annotations

from .base import Variable


class Precipitation(Variable):
    """Rain and snow as a monthly total, so years aggregate by sum, not mean."""

    variable_id = "precipitation"
    alias = "precipitation"
    #: A mean of monthly totals is not an annual total; this override is
    #: pinned by a test and by ``analysis.run.ANNUAL_AGG``.
    annual_agg = "sum"
