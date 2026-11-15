"""Comparison keeps the table and refuses an unsupported order."""

from __future__ import annotations

import pytest

import terralens as tl
from terralens._compare import compare, intervals_overlap

BANNED = ("because", "due to", "caused", "proves")


def test_interval_overlap_is_inclusive():
    assert intervals_overlap((0.0, 1.0), (1.0, 2.0)) is True
    assert intervals_overlap((0.0, 1.0), (1.1, 2.0)) is False
    assert intervals_overlap(None, (0.0, 1.0)) is False


def test_two_regions_compare_and_overlap_is_stated():
    comparison = compare("ireland", "sahel", variables=["temperature"])
    assert len(comparison.table) == 1
    text = str(comparison)
    assert "overlap" in text.lower()
    assert "temperature" in text.lower() or "Air temperature" in text


def test_summary_text_never_claims_causation():
    comparison = compare("ireland", "us_southwest", variables=["t2m"])
    lowered = str(comparison).lower()
    for word in BANNED:
        assert word not in lowered


def test_ranking_names_a_faster_region():
    comparison = compare("ireland", "sahel", variables=["temperature"])
    faster = comparison.ranking.iloc[0]["faster"]
    assert faster in {"ireland", "sahel"}


def test_unknown_variable_lists_the_valid_names():
    with pytest.raises(ValueError) as caught:
        compare("ireland", "sahel", variables=["rainfall"])
    assert "precipitation" in str(caught.value)


def test_compare_plot_returns_a_figure():
    comparison = compare("ireland", "sahel", variables=["temperature"])
    figure = comparison.plot()
    assert figure.__class__.__name__ == "Figure"


def test_public_compare_survives_repeated_calls():
    """The lazy submodule import must not replace ``tl.compare`` with the module."""
    first = tl.compare("ireland", "sahel", variables=["temperature"])
    second = tl.compare("ireland", "sahel", variables=["temperature"])

    assert callable(tl.compare)
    assert first.table.equals(second.table)
