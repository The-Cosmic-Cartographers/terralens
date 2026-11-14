"""Per-variable defaults for the Lineup, from Linear docs 11 and 10.

These are the five rows Kevin verified in Giovanni on 14 Nov plus the OMI NO2
field name that the verification corrected. They are defaults for the CLI only;
every value can be overridden, and provenance records what was actually used.
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
    ),
    "soil_moisture_0_10": Variable(
        variable_id="soil_moisture_0_10",
        dataset_id="gldas_noah025_m21",
        product="GLDAS-2.1 Noah monthly soil moisture, 0-10 cm (GLDAS_NOAH025_M)",
        version="2.1",
        native_unit="kg/m2",
        output_unit="kg/m2",
        spatial_resolution="0.25°",
        giovanni_variable_id="SoilMoi0_10cm_inst",
    ),
    "evapotranspiration": Variable(
        variable_id="evapotranspiration",
        dataset_id="gldas_noah025_m21",
        product="GLDAS-2.1 Noah monthly evapotranspiration (GLDAS_NOAH025_M)",
        version="2.1",
        native_unit="kg/m2/s",
        output_unit="mm/day",
        spatial_resolution="0.25°",
        giovanni_variable_id="Evap_tavg",
    ),
    "precipitation": Variable(
        variable_id="precipitation",
        dataset_id="gpm_3imergm_v07",
        product="GPM IMERG Final monthly precipitation (GPM_3IMERGM)",
        version="V07",
        native_unit="mm/hr",
        output_unit="mm/month",
        spatial_resolution="0.1°",
        giovanni_variable_id="precipitation",
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
    ),
}
