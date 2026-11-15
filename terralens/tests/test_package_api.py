"""The public surface, lazy access and helpful errors."""

from __future__ import annotations

import pytest

import terralens as tl
from terralens import cache

EXPECTED = ["iberia", "ireland", "nw_south_asia", "sahel", "us_southwest"]


def test_list_regions_is_the_five_poc_regions():
    assert tl.list_regions() == EXPECTED


def test_region_attribute_is_lazy_and_works():
    ireland = tl.ireland
    assert ireland.region_id == "ireland"
    assert ireland.name == "Ireland"


def test_unknown_region_suggests_the_closest_id():
    with pytest.raises(AttributeError) as caught:
        tl.ierland  # noqa: B018 - attribute access is the test
    message = str(caught.value)
    assert "ireland" in message
    assert "sahel" in message


def test_info_reads_no_parquet(monkeypatch):
    import pandas as pd

    def refuse(*_args, **_kwargs):
        raise AssertionError("region.info() must not read a parquet file")

    monkeypatch.setattr(pd, "read_parquet", refuse)
    text = tl.ireland.info()
    assert "temperature" in text
    assert "available" in text


def test_data_root_can_be_overridden(monkeypatch, tmp_path):
    monkeypatch.setenv("TERRALENS_DATA", str(tmp_path))
    assert cache.data_root() == tmp_path.resolve()


def test_region_summary_has_one_row_per_available_variable():
    summary = tl.ireland.summary()
    assert list(summary.columns)[:4] == ["variable", "dataset", "per_decade", "unit"]
    assert len(summary) == len(tl.ireland.available_variables()) >= 5
    assert summary["per_decade"].notna().all()
