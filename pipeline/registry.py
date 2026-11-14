"""Per-variable defaults for the Lineup, from Linear docs 11 and 10.

These are the row defaults for the Lineup: the five rows Kevin verified in Giovanni
on 14 Nov plus the OMI NO2 field name that the verification corrected. They are
defaults for the CLI only; every value can be overridden, and provenance records
what was actually used.

The window fields are D21 (doc 10): whole calendar years, fixed per variable so
two regions of the same row can never be compared over different periods. T2M
starts in 1981 even though MERRA-2 begins in 1980; IMERG stops at 2024 because
the Giovanni product ends on 2025-09-30.
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
    "soil_moisture_0_10": Variable(
        variable_id="soil_moisture_0_10",
        dataset_id="gldas_noah025_m21_soilmoi0_10",
        product="GLDAS-2.1 Noah monthly soil moisture, 0-10 cm (GLDAS_NOAH025_M)",
        version="2.1",
        native_unit="kg/m2",
        output_unit="kg/m2",
        spatial_resolution="0.25°",
        giovanni_variable_id="SoilMoi0_10cm_inst",
        start_year=2000,
        end_year=2025,
    ),
    "evapotranspiration": Variable(
        variable_id="evapotranspiration",
        dataset_id="gldas_noah025_m21_evap",
        product="GLDAS-2.1 Noah monthly evapotranspiration (GLDAS_NOAH025_M)",
        version="2.1",
        native_unit="kg/m2/s",
        output_unit="mm/day",
        spatial_resolution="0.25°",
        giovanni_variable_id="Evap_tavg",
        start_year=2000,
        end_year=2025,
    ),
    "precipitation": Variable(
        variable_id="precipitation",
        dataset_id="gpm_3imergm_v07",
        # Pinned to the V07B reprocessed run (NAS-57): the granule filenames carry
        # `.V07B`, and V07 and V07B must never be mixed inside one series.
        product="GPM IMERG Final monthly precipitation, V07B reprocessed run (GPM_3IMERGM)",
        version="V07B",
        native_unit="mm/hr",
        output_unit="mm/month",
        spatial_resolution="0.1°",
        giovanni_variable_id="precipitation",
        start_year=2001,
        end_year=2024,
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
        start_year=2003,
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
