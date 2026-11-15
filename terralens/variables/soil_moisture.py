"""Soil moisture, 0-5 cm (MERRA-2 M2TMNXLND SFMC)."""

from __future__ import annotations

from .base import Variable


class SoilMoisture(Variable):
    """Volumetric water in the top 5 cm of soil, in m3/m3 (model output)."""

    variable_id = "soil_moisture_0_5"
    alias = "soil_moisture"
