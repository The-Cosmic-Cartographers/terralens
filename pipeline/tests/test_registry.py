"""The registry pins the product versions the pull is allowed to use (NAS-57)."""

from __future__ import annotations

from pipeline.registry import VARIABLES


def test_imerg_is_pinned_to_the_v07b_reprocessed_run() -> None:
    """GES DISC serves V07B granules; a silent move back to V07 must fail here."""
    precipitation = VARIABLES["precipitation"]
    assert precipitation.version == "V07B"
    assert "V07B" in precipitation.product
    assert precipitation.dataset_id == "gpm_3imergm_v07b"


def test_every_variable_has_a_window_and_a_unit() -> None:
    for variable in VARIABLES.values():
        assert variable.start_year < variable.end_year
        assert variable.native_unit
        assert variable.output_unit
        assert variable.giovanni_variable_id
