"""Tests for the Giovanni CSV parser (NAS-7)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pipeline.giovanni import GiovanniParseError, parse_giovanni_csv, read_giovanni_csv

SAMPLE = Path(__file__).parent / "data" / "giovanni_t2m_sample.csv"


def test_reads_sample_with_comment_and_unit_block() -> None:
    frame = read_giovanni_csv(SAMPLE)
    assert len(frame) == 24
    assert frame["timestamp"].iloc[0] == pd.Timestamp("1981-01-01")
    assert frame["timestamp"].iloc[-1] == pd.Timestamp("1982-12-01")
    assert frame["value"].iloc[0] == pytest.approx(283.15)


def test_skips_notes_appended_after_the_table() -> None:
    text = (
        "Month,Mean\n2000-01,1.5\n2000-02,1.6\n\nNote: values are area averages\nSource: Giovanni\n"
    )
    frame = parse_giovanni_csv(text)
    assert list(frame["value"]) == [1.5, 1.6]


def test_missing_markers_become_null() -> None:
    text = "Month,T2M\n2000-01,1.5\n2000-02,-999\n2000-03,\n2000-04,NaN\n"
    frame = parse_giovanni_csv(text)
    assert frame["value"].isna().sum() == 3
    assert frame["value"].dropna().iloc[0] == pytest.approx(1.5)


def test_duplicate_months_keep_the_last_row() -> None:
    text = "Month,Mean\n2000-01,1.0\n2000-01,2.0\n"
    frame = parse_giovanni_csv(text)
    assert len(frame) == 1
    assert frame["value"].iloc[0] == pytest.approx(2.0)


def test_full_iso_dates_are_accepted() -> None:
    text = "Date,Value\n2000-01-01,3.0\n2000-02-01,3.5\n"
    frame = parse_giovanni_csv(text)
    assert len(frame) == 2
    assert frame["timestamp"].iloc[0] == pd.Timestamp("2000-01-01")


def test_rejects_a_file_without_a_table() -> None:
    with pytest.raises(GiovanniParseError):
        parse_giovanni_csv("# only comments and notes\nNothing here\n")
