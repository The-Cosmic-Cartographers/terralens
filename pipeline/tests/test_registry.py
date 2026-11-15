"""The registry pins the product versions the pull is allowed to use (NAS-57)."""

from __future__ import annotations

from pipeline.registry import VARIABLES


def test_the_lineup_rows_are_pinned_to_merra2_v5_12_4() -> None:
    """All five Lineup rows come from MERRA-2 5.12.4 so the long record is one system.

    T2M starts in 1981 (the committed, verified Giovanni series); the other four use
    the full 1980-2025 MERRA-2 window.
    """
    for variable_id in (
        "t2m",
        "soil_moisture_0_5",
        "evapotranspiration",
        "precipitation",
        "aerosol",
    ):
        spec = VARIABLES[variable_id]
        assert spec.version == "5.12.4", variable_id
        assert spec.dataset_id.startswith("merra2_"), variable_id
        assert spec.end_year == 2025, variable_id
    assert VARIABLES["t2m"].start_year == 1981
    for variable_id in ("soil_moisture_0_5", "evapotranspiration", "precipitation", "aerosol"):
        assert VARIABLES[variable_id].start_year == 1980, variable_id


def test_every_variable_has_a_window_and_a_unit() -> None:
    for variable in VARIABLES.values():
        assert variable.start_year < variable.end_year
        assert variable.native_unit
        assert variable.output_unit
        assert variable.giovanni_variable_id
