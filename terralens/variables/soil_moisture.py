"""Soil moisture, 0-10 cm (GLDAS-2.1 Noah)."""

from __future__ import annotations

from .base import Variable


class SoilMoisture(Variable):
    """Water held in the top soil layer, in kg/m2 (equivalent to mm of water)."""

    variable_id = "soil_moisture_0_10"
    alias = "soil_moisture"
