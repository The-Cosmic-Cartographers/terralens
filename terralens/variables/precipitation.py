"""Precipitation (MERRA-2 M2TMNXFLX PRECTOTCORR), reported in mm/month."""

from __future__ import annotations

from .base import Variable


class Precipitation(Variable):
    """Rain and snow as a monthly total, so years aggregate by sum, not mean.

    This is MERRA-2 bias-corrected model output, not the IMERG satellite estimate.
    """

    variable_id = "precipitation"
    alias = "precipitation"
    #: A mean of monthly totals is not an annual total; this override is
    #: pinned by a test and by ``analysis.run.ANNUAL_AGG``.
    annual_agg = "sum"
