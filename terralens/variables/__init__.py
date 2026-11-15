"""The five POC variables, keyed by their Python alias."""

from __future__ import annotations

from .aerosol import Aerosol
from .base import Variable
from .evapotranspiration import Evapotranspiration
from .precipitation import Precipitation
from .soil_moisture import SoilMoisture
from .temperature import Temperature

VARIABLE_CLASSES: dict[str, type[Variable]] = {
    Temperature.alias: Temperature,
    SoilMoisture.alias: SoilMoisture,
    Evapotranspiration.alias: Evapotranspiration,
    Precipitation.alias: Precipitation,
    Aerosol.alias: Aerosol,
}

BY_VARIABLE_ID = {cls.variable_id: cls for cls in VARIABLE_CLASSES.values()}

__all__ = [
    "VARIABLE_CLASSES",
    "BY_VARIABLE_ID",
    "Variable",
    "Temperature",
    "SoilMoisture",
    "Evapotranspiration",
    "Precipitation",
    "Aerosol",
]
