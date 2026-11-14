"""The same row belongs to two BH families (D23, NAS-28).

The contract has no single correct adjusted p-value for a region/variable: it
depends on the family. `lineup/<region>.json` carries the lineup adjustment and
`<dataset_id>/trends.json` the compare one, and `/trend` deliberately serves the
lineup copy so a detail card cannot disagree with the board above it.
"""

from __future__ import annotations

import pytest

from analysis.run import apply_bh, apply_compare_family


def row(variable_id: str, region_id: str, p_value: float | None) -> dict:
    return {
        "dataset_id": "d",
        "variable_id": variable_id,
        "region_id": region_id,
        "p_value": p_value,
        "adjusted_p_value": None,
        "significant_at_0_05": False,
        "verdict": None,
        "trend_direction": "increasing",
        "sen_slope_per_year": 0.1,
        "detect_years": 40.0,
        "effect_size_swings": 1.0,
        "bh_family": f"lineup:{region_id}",
        "caveats": [],
    }


def test_compare_family_corrects_across_regions_for_one_variable():
    rows = [
        row("t2m", "ireland", 0.01),
        row("t2m", "sahel", 0.02),
        row("t2m", "us_southwest", 0.03),
        row("precipitation", "ireland", 0.60),
    ]

    compare = apply_compare_family(rows)

    t2m = [r for r in compare if r["variable_id"] == "t2m"]
    assert all(r["bh_family"] == "compare:t2m" for r in t2m)
    # three tests: the smallest p is multiplied by three, then the step-up
    # monotone rule pulls the others down to it
    assert [r["adjusted_p_value"] for r in t2m] == pytest.approx([0.03, 0.03, 0.03])
    rain = next(r for r in compare if r["variable_id"] == "precipitation")
    assert rain["bh_family"] == "compare:precipitation"
    assert rain["adjusted_p_value"] == pytest.approx(0.60)


def test_withheld_rows_stay_out_of_the_compare_family():
    rows = [
        row("t2m", "ireland", 0.01),
        row("t2m", "sahel", None),
    ]

    compare = apply_compare_family(rows)

    held = next(r for r in compare if r["region_id"] == "sahel")
    assert held["adjusted_p_value"] is None
    assert held["verdict"] == "not_enough_data"
    ireland = next(r for r in compare if r["region_id"] == "ireland")
    assert ireland["adjusted_p_value"] == pytest.approx(0.01)


def test_one_row_gets_a_different_adjusted_p_in_each_family():
    rows = [row("t2m", "ireland", 0.001), row("precipitation", "ireland", 0.20)]

    lineup_rows = [dict(r) for r in rows]
    apply_bh(lineup_rows)
    compare_rows = apply_compare_family([dict(r) for r in rows])

    lineup_t2m = next(r for r in lineup_rows if r["variable_id"] == "t2m")
    compare_t2m = next(r for r in compare_rows if r["variable_id"] == "t2m")

    # two tests in the lineup, one in the compare family
    assert lineup_t2m["adjusted_p_value"] == pytest.approx(0.002)
    assert compare_t2m["adjusted_p_value"] == pytest.approx(0.001)
    assert lineup_t2m["bh_family"] == "lineup:ireland"
    assert compare_t2m["bh_family"] == "compare:t2m"


def test_significant_compare_rows_do_not_carry_detectability():
    rows = [row("t2m", "ireland", 1e-06)]

    compare = apply_compare_family(rows)

    assert compare[0]["verdict"] == "significant"
    assert compare[0]["detect_years"] is None
