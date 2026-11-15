"""Evapotranspiration (MERRA-2 M2TMNXLND EVLAND), reported in mm/day."""

from __future__ import annotations

from .base import Variable


class Evapotranspiration(Variable):
    """Water leaving the land through plants and evaporation."""

    variable_id = "evapotranspiration"
    alias = "evapotranspiration"
