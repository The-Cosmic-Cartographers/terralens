"""Benjamini-Hochberg over an explicit family of results."""

from __future__ import annotations

import pytest

import terralens as tl
from terralens.trends import TrendResult


def _result(p_value: float | None, *, per_decade: float = 1.0) -> TrendResult:
    if p_value is None:
        verdict, direction = "not_enough_data", "withheld"
    elif p_value < 0.05:
        verdict, direction = "significant", "increasing"
    elif p_value < 0.10:
        verdict, direction = "weak_evidence", "no_significant_trend"
    else:
        verdict, direction = "no_clear_trend", "no_significant_trend"
    return TrendResult(
        variable_id="t2m",
        region_id="ireland",
        dataset_id="sample_t2m",
        label="Air temperature (2 m)",
        unit="°C",
        per_decade=per_decade,
        confidence_interval_95=(0.1, 0.2),
        p_value=p_value,
        n_obs=540,
        period=(1981, 2025),
        direction=direction,
        method="seasonal_mann_kendall_hamed_rao + sens_slope",
        verdict=verdict,
        caveats=(),
        family_size=1,
        citation="sample",
    )


def test_known_family_matches_benjamini_hochberg():
    results = [_result(p) for p in (0.001, 0.01, 0.04, 0.20)]

    adjusted = tl.adjust_bh(results)

    assert [r.adjusted_p_value for r in adjusted] == pytest.approx(
        [0.004, 0.02, 0.0533333333, 0.20]
    )
    assert [r.family_size for r in adjusted] == [4, 4, 4, 4]
    assert [r.p_value for r in adjusted] == [0.001, 0.01, 0.04, 0.20]
    assert [r.verdict for r in adjusted] == [
        "significant",
        "significant",
        "weak_evidence",
        "no_clear_trend",
    ]
    assert [r.direction for r in adjusted] == [
        "increasing",
        "increasing",
        "no_significant_trend",
        "no_significant_trend",
    ]


def test_order_is_preserved_and_direction_follows_the_slope():
    adjusted = tl.adjust_bh([_result(0.20), _result(0.01, per_decade=-2.0)])

    assert [r.p_value for r in adjusted] == [0.20, 0.01]
    assert [r.adjusted_p_value for r in adjusted] == pytest.approx([0.20, 0.02])
    assert adjusted[1].verdict == "significant"
    assert adjusted[1].direction == "decreasing"


def test_withheld_results_stay_outside_the_family():
    held = _result(None)

    adjusted = tl.adjust_bh([_result(0.01), _result(0.04), held])

    assert adjusted[2].adjusted_p_value is None
    assert adjusted[2].family_size == 2
    assert "withheld" in adjusted[2].warnings[-1]
    assert adjusted[0].family_size == 2
    assert adjusted[1].adjusted_p_value == pytest.approx(0.04)


def test_a_family_of_one_is_left_unadjusted():
    original = _result(0.03)

    adjusted = tl.adjust_bh([original])

    assert adjusted == [original]
    assert adjusted[0].adjusted_p_value is None
    assert adjusted[0].family_size == 1
    assert "unadjusted" in adjusted[0].warnings[-1]


def test_adjusted_warning_and_serialisation():
    adjusted = tl.adjust_bh([_result(0.001), _result(0.01)])

    assert "unadjusted" in _result(0.001).warnings[-1]
    assert "Benjamini-Hochberg" in adjusted[0].warnings[-1]
    assert "q=0.002" in repr(adjusted[0])
    assert adjusted[0].to_dict()["adjusted_p_value"] == pytest.approx(0.002)


def test_rejects_non_trend_results():
    with pytest.raises(TypeError, match="TrendResult"):
        tl.adjust_bh([object()])
