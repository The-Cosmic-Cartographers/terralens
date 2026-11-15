"""Per-variable defaults for the Lineup, from Linear docs 11 and 10.

These are the source definitions for the five MVP rows, with NO2 retained for a
later route decision. Provenance records the product and field actually used.

The window fields are D21 (doc 10): whole calendar years, fixed per variable so
two regions of the same row can never be compared over different periods. The
five MVP rows now use the same MERRA-2 monthly window, 1980–2025.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Variable:
    """Everything the pipeline needs to label one Lineup row."""

    variable_id: str
    dataset_id: str
    product: str
    version: str
    native_unit: str
    output_unit: str
    spatial_resolution: str
    giovanni_variable_id: str
    start_year: int
    end_year: int


VARIABLES: dict[str, Variable] = {
    "t2m": Variable(
        variable_id="t2m",
        dataset_id="merra2_m2tmnxslv",
        product="MERRA-2 2 m air temperature (M2TMNXSLV)",
        version="5.12.4",
        native_unit="K",
        output_unit="°C",
        spatial_resolution="0.5° x 0.625°",
        giovanni_variable_id="T2M",
        start_year=1981,
        end_year=2025,
    ),
    "soil_moisture_0_5": Variable(
        variable_id="soil_moisture_0_5",
        dataset_id="merra2_m2tmnxlnd_sfmc_v5_12_4",
        product="MERRA-2 monthly volumetric soil moisture, 0-5 cm surface layer (M2TMNXLND SFMC)",
        version="5.12.4",
        native_unit="m3/m3",
        output_unit="m3/m3",
        spatial_resolution="0.5° x 0.625°",
        giovanni_variable_id="SFMC",
        start_year=1980,
        end_year=2025,
    ),
    "evapotranspiration": Variable(
        variable_id="evapotranspiration",
        dataset_id="merra2_m2tmnxlnd_evland_v5_12_4",
        product="MERRA-2 monthly land evapotranspiration (M2TMNXLND EVLAND)",
        version="5.12.4",
        native_unit="kg m-2 s-1",
        output_unit="mm/day",
        spatial_resolution="0.5° x 0.625°",
        giovanni_variable_id="EVLAND",
        start_year=1980,
        end_year=2025,
    ),
    "precipitation": Variable(
        variable_id="precipitation",
        dataset_id="merra2_m2tmnxflx_prectotcorr_v5_12_4",
        product="MERRA-2 monthly bias-corrected total precipitation (M2TMNXFLX PRECTOTCORR)",
        version="5.12.4",
        native_unit="kg m-2 s-1",
        output_unit="mm/month",
        spatial_resolution="0.5° x 0.625°",
        giovanni_variable_id="PRECTOTCORR",
        start_year=1980,
        end_year=2025,
    ),
    "aerosol": Variable(
        variable_id="aerosol",
        dataset_id="merra2_m2tmnxaer_v5_12_4",
        product="MERRA-2 total aerosol extinction AOT at 550 nm (M2TMNXAER)",
        version="5.12.4",
        native_unit="1",
        output_unit="1",
        spatial_resolution="0.5° x 0.625°",
        giovanni_variable_id="TOTEXTTAU",
        start_year=1980,
        end_year=2025,
    ),
    "no2": Variable(
        variable_id="no2",
        dataset_id="omi_omno2d_v004",
        product="OMI-Aura daily tropospheric NO2 column, 30% cloud screened (OMNO2d)",
        version="v004",
        native_unit="molec/cm2",
        output_unit="molec/cm2",
        spatial_resolution="0.25°",
        giovanni_variable_id="ColumnAmountNO2TropCloudScreened",
        start_year=2005,
        end_year=2025,
    ),
}
