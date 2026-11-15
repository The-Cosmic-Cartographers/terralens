"""Labels and per-variable presentation defaults.

Kept inside the package because the library needs them and the wheel must not
ship the repo-only ``analysis`` or ``pipeline`` packages.
"""

from __future__ import annotations

# Plain-language labels for each Lineup row.
LABELS: dict[str, str] = {
    "t2m": "Air temperature (2 m)",
    "soil_moisture_0_5": "Soil moisture (0-5 cm)",
    "evapotranspiration": "Evapotranspiration",
    "precipitation": "Precipitation",
    "aerosol": "Aerosol optical depth",
    "no2": "NO2 column (troposphere)",
}

PRODUCT_TYPE: dict[str, str] = {
    "t2m": "reanalysis",
    "aerosol": "reanalysis",
    "soil_moisture_0_5": "reanalysis",
    "evapotranspiration": "reanalysis",
    "precipitation": "reanalysis",
    "no2": "satellite",
}

# Precipitation is a monthly total, so its annual aggregate is a sum; every
# other row is a state, so the annual mean is the right aggregate.
ANNUAL_AGG: dict[str, str] = {"precipitation": "sum"}

# The Sen slope is fitted to the annual aggregate, so for a summed variable its
# unit is the annual total, not the monthly value the series is stored in.
SLOPE_BASE_UNIT: dict[str, str] = {"precipitation": "mm (annual total)"}
