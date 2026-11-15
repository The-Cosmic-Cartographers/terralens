"""Aerosol optical thickness (MERRA-2 M2TMNXAER)."""

from __future__ import annotations

from .base import Variable


class Aerosol(Variable):
    """Total aerosol extinction at 550 nm, dimensionless."""

    variable_id = "aerosol"
    alias = "aerosol"
