"""Tests for the generated References list (NAS-43)."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.references import citations, render, short_name, tools


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
                "permalink": "https://giovanni.gsfc.nasa.gov/giovanni/#service=ArAvTs&bbox=-10.5",
            }
        },
    }
    base.update(overrides)
    return base


def test_short_name_reads_the_parenthesised_dataset_id() -> None:
    assert short_name("MERRA-2 2 m air temperature (M2TMNXSLV)") == "M2TMNXSLV"
    assert short_name("something without an id") == "something without an id"


def test_citation_follows_the_doc_11_template_and_carries_the_permalink() -> None:
    (line,) = citations(_provenance())
    assert line.startswith(
        "NASA GES DISC Giovanni, *MERRA-2 2 m air temperature*, M2TMNXSLV v5.12.4, "
        "Ireland (-10.5,51.4,-6.0,55.4), 1981-01–2025-12, accessed 2026-11-14."
    )
    assert line.rstrip().endswith("bbox=-10.5")


def test_citation_falls_back_to_the_dataset_url_without_a_region_permalink() -> None:
    provenance = _provenance(doi_or_url="https://giovanni.gsfc.nasa.gov/giovanni/#data=M2TMNXSLV")
    provenance["regions"]["ireland"].pop("permalink")
    (line,) = citations(provenance)
    assert "data=M2TMNXSLV" in line


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


def test_tools_come_from_the_declared_dependencies(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\ndependencies = ["pandas>=2.2", "scipy>=1.13"]\n'
        '[dependency-groups]\ndev = ["pytest>=8"]\n',
        encoding="utf-8",
    )
    found = tools(pyproject)
    assert "`pandas>=2.2`" in found
    assert "`pytest>=8` (development)" in found


def test_tools_of_a_missing_pyproject_are_empty(tmp_path: Path) -> None:
    assert tools(tmp_path / "nope.toml") == []


def test_render_has_every_section_the_ticket_asks_for(tmp_path: Path) -> None:
    path = tmp_path / "provenance.json"
    path.write_text(json.dumps(_provenance()), encoding="utf-8")

    page = render([path])

    for heading in ("# References", "## Data", "## Software", "## Methods", "## Not used"):
        assert heading in page
    assert "Mann, H. B. (1945)" in page
    assert "Hamed, K. H., & Rao, A. R. (1998)" in page
    assert "KNMI Climate Explorer" in page
    assert "not cited" in page


def test_render_deduplicates_and_lists_nothing_gracefully(tmp_path: Path) -> None:
    assert "(no processed series yet)" in render([])

    path = tmp_path / "provenance.json"
    path.write_text(json.dumps(_provenance()), encoding="utf-8")
    once = render([path])
    twice = render([path, path])
    assert once == twice
    assert once.count("NASA GES DISC Giovanni") == 1
