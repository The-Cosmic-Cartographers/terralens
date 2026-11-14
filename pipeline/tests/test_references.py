"""Tests for the generated References list (NAS-43)."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.references import citations, render, short_name


def _provenance(**overrides: object) -> dict:
    base = {
        "dataset_id": "merra2_m2tmnxslv",
        "product": "MERRA-2 2 m air temperature (M2TMNXSLV)",
        "version": "5.12.4",
        "access_date": "2026-11-14",
        "regions": {
            "ireland": {
                "requested_box": "-10.5,51.4,-6.0,55.4",
                "period_start": "1981-01-01",
                "period_end": "2025-12-01",
            }
        },
    }
    base.update(overrides)
    return base


def test_short_name_reads_the_parenthesised_dataset_id() -> None:
    assert short_name("MERRA-2 2 m air temperature (M2TMNXSLV)") == "M2TMNXSLV"
    assert short_name("something without an id") == "something without an id"


def test_citation_follows_the_doc_11_template() -> None:
    (line,) = citations(_provenance())
    assert line == (
        "NASA GES DISC Giovanni, *MERRA-2 2 m air temperature*, M2TMNXSLV v5.12.4, "
        "Ireland (-10.5,51.4,-6.0,55.4), 1981-01–2025-12, accessed 2026-11-14."
    )


def test_each_region_gets_its_own_box_and_window() -> None:
    provenance = _provenance()
    provenance["regions"]["sahel"] = {
        "requested_box": "0.0,12.0,20.0,18.0",
        "period_start": "1981-01-01",
        "period_end": "2025-12-01",
    }
    lines = citations(provenance)
    assert len(lines) == 2
    assert any("Sahel (0.0,12.0,20.0,18.0)" in line for line in lines)
    assert any("Ireland (" in line for line in lines)


def test_region_labels_keep_capitals() -> None:
    provenance = _provenance()
    provenance["regions"] = {"us_southwest": provenance["regions"]["ireland"]}
    (line,) = citations(provenance)
    assert "US Southwest (" in line


def test_render_deduplicates_and_lists_nothing_gracefully(tmp_path: Path) -> None:
    empty = render([])
    assert "(no processed series yet)" in empty

    path = tmp_path / "provenance.json"
    path.write_text(json.dumps(_provenance()), encoding="utf-8")
    once = render([path])
    twice = render([path, path])
    assert once == twice
    assert once.count("NASA GES DISC Giovanni") == 1
    assert once.startswith("# References")
