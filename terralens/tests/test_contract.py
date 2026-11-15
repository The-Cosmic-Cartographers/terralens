"""Contract tests: the package must not disagree with the shipped results."""

from __future__ import annotations

import json

import pytest

import terralens as tl
from terralens.cache import results_path
from terralens.variables import VARIABLE_CLASSES


def test_ireland_t2m_matches_the_committed_lineup_row():
    lineup = json.loads(results_path("lineup", "ireland.json").read_text(encoding="utf-8"))
    row = next(row for row in lineup["rows"] if row["variable_id"] == "t2m")
    committed = row["trend"]

    result = tl.ireland.temperature.trend()

    assert result.per_decade == pytest.approx(committed["sen_slope_per_year"] * 10, abs=1e-12)
    assert result.p_value == pytest.approx(committed["p_value"], abs=1e-12)
    low, high = committed["confidence_interval_95"]
    assert result.confidence_interval_95 == pytest.approx((low * 10, high * 10), abs=1e-12)
    assert result.family_size == 1
    assert result.n_obs == committed["observation_count"]


def test_every_variable_loads_and_trends_for_ireland():
    for alias in VARIABLE_CLASSES:
        variable = getattr(tl.ireland, alias)
        frame = variable.load()
        assert len(frame) > 100, alias
        assert frame["value"].notna().any(), alias
        trend = variable.trend()
        assert trend.per_decade is not None, alias
        assert trend.citation and trend.dataset_id, alias


def test_precipitation_aggregates_annually_by_sum():
    from terralens.variables import Precipitation

    assert Precipitation.annual_agg == "sum"
    annual = tl.ireland.precipitation.annual()
    values = [value for _, value in annual if value is not None]
    assert values
    # Monthly means are ~25-340 mm; an annual sum is far above any single month.
    assert min(values) > 500


def test_trend_serialisation_round_trips():
    result = tl.ireland.temperature.trend()
    payload = result.to_dict()
    assert payload["period_start"] == result.period[0]
    assert payload["slope_per_year"] == pytest.approx(result.per_decade / 10)
    assert json.loads(result.to_json())["variable_id"] == "t2m"
    csv_text = result.to_csv()
    assert csv_text.count("\n") == 2
    assert "per_decade" in csv_text
