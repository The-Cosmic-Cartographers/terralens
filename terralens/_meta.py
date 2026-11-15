"""Labels and per-variable presentation defaults.

Kept inside the package because the library needs them and the wheel must not
ship the repo-only ``analysis`` or ``pipeline`` packages.
"""

from __future__ import annotations

# Plain-language labels for each Lineup row.
LABELS: dict[str, str] = {
    "t2m": "Air temperature (2 m)",
    "soil_moisture_0_10": "Soil moisture (0-10 cm)",
    "evapotranspiration": "Evapotranspiration",
    "precipitation": "Precipitation",
    "aerosol": "Aerosol optical depth",
    "no2": "NO2 column (troposphere)",
}

PRODUCT_TYPE: dict[str, str] = {
    "t2m": "reanalysis",
    "aerosol": "reanalysis",
    "soil_moisture_0_10": "land_model",
    "evapotranspiration": "land_model",
    "precipitation": "satellite",
    "no2": "satellite",
}

# Precipitation is a monthly total, so its annual aggregate is a sum; every
# other row is a state, so the annual mean is the right aggregate.
ANNUAL_AGG: dict[str, str] = {"precipitation": "sum"}
