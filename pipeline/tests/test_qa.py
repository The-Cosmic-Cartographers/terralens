"""Tests for the processed-data QA checks (NAS-41)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from pipeline import qa
from pipeline.registry import VARIABLES


def _frames(
    tmp_path: Path, variable_id: str = "t2m", months: int | None = None
) -> tuple[Path, Path]:
    """Write a minimal processed dataset + raw CSV that should pass every check."""
    spec = VARIABLES[variable_id]
    if months is None:
        months = (spec.end_year - spec.start_year + 1) * 12
    dataset = tmp_path / "processed" / spec.dataset_id
    dataset.mkdir(parents=True)
    raw = tmp_path / "raw"
    raw.mkdir(exist_ok=True)

    timestamps = pd.date_range(f"{spec.start_year}-01-01", periods=months, freq="MS")
    frame = pd.DataFrame(
        {
            "dataset_id": [spec.dataset_id] * months,
            "variable_id": [spec.variable_id] * months,
            "region_id": ["ireland"] * months,
            "timestamp": timestamps,
            "value": [1.0] * months,
            "unit": [spec.output_unit] * months,
            "anomaly": pd.array([pd.NA] * months, dtype="Float64"),
            "valid_cell_count": pd.array([pd.NA] * months, dtype="Int64"),
            "total_cell_count": pd.array([pd.NA] * months, dtype="Int64"),
            "coverage_fraction": pd.array([pd.NA] * months, dtype="Float64"),
            "quality_summary": ["test"] * months,
            "source": ["test"] * months,
            "n_valid_days": pd.array([pd.NA] * months, dtype="Int64"),
        }
    )
    frame.to_parquet(dataset / "ireland.parquet", index=False)

    source = raw / "t2m_ireland.csv"
    source.write_text("Unit,K\nMonth,Mean\n1981-01,290.0\n", encoding="utf-8")

    provenance = {
        "dataset_id": spec.dataset_id,
        "product": spec.product,
        "version": spec.version,
        "access_date": "2026-11-14",
        "access_route": "NASA GES DISC / Giovanni",
        "variable_field": spec.giovanni_variable_id,
        "native_unit": spec.native_unit,
        "output_unit": spec.output_unit,
        "spatial_resolution": spec.spatial_resolution,
        "doi_or_url": "https://example.invalid/job",
        "regions": {
            "ireland": {
                "requested_box": "-10.5,51.4,-6.0,55.4",
                "period_start": timestamps[0].date().isoformat(),
                "period_end": timestamps[-1].date().isoformat(),
                "giovanni_variable_id": spec.giovanni_variable_id,
                "permalink": "https://example.invalid/job",
                "source_csv": source.name,
                "source_csv_sha256": qa._sha256(source),
            }
        },
    }
    (dataset / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
    return dataset, raw


def test_a_clean_dataset_has_no_issues(tmp_path: Path) -> None:
    dataset, raw = _frames(tmp_path)
    issues = qa.check_dataset(dataset, raw)
    assert [issue for issue in issues if issue.level == "error"] == []


def test_missing_contract_column_is_an_error_but_does_not_hide_the_hash(tmp_path: Path) -> None:
    dataset, raw = _frames(tmp_path)
    frame = pd.read_parquet(dataset / "ireland.parquet").drop(columns=["n_valid_days"])
    frame.to_parquet(dataset / "ireland.parquet", index=False)
    (raw / "t2m_ireland.csv").write_text("Unit,K\nMonth,Mean\n1981-01,1.0\n", encoding="utf-8")

    messages = [issue.message for issue in qa.check_dataset(dataset, raw) if issue.level == "error"]
    assert any("n_valid_days" in message for message in messages)
    assert any("is not the export this series was built from" in message for message in messages)


def test_an_export_that_is_not_in_the_repo_is_a_warning_not_an_error(
    tmp_path: Path,
) -> None:
    """data/raw is not committed, so a missing export is unverifiable, not wrong."""
    dataset, raw = _frames(tmp_path)
    (raw / "t2m_ireland.csv").unlink()

    issues = qa.check_dataset(dataset, raw)
    assert [issue for issue in issues if issue.level == "error"] == []
    assert any("is not in the repo" in issue.message for issue in issues)
    assert any(issue.level == "warning" for issue in issues)


def test_a_different_file_with_the_recorded_name_says_so_plainly(tmp_path: Path) -> None:
    dataset, raw = _frames(tmp_path)
    (raw / "t2m_ireland.csv").write_text("Unit,K\nMonth,Mean\n1981-01,1.0\n", encoding="utf-8")

    messages = [issue.message for issue in qa.check_dataset(dataset, raw) if issue.level == "error"]
    assert any("is not the export this series was built from" in message for message in messages)
    assert any("restore that export or rebuild" in message for message in messages)


def test_wrong_stored_unit_is_an_error(tmp_path: Path) -> None:
    dataset, raw = _frames(tmp_path)
    frame = pd.read_parquet(dataset / "ireland.parquet")
    frame["unit"] = "K"
    frame.to_parquet(dataset / "ireland.parquet", index=False)
    messages = [issue.message for issue in qa.check_dataset(dataset, raw)]
    assert any("stored unit" in message for message in messages)


def test_a_gap_in_the_window_is_an_error(tmp_path: Path) -> None:
    dataset, raw = _frames(tmp_path)
    frame = pd.read_parquet(dataset / "ireland.parquet").iloc[[0, 2]]
    frame.to_parquet(dataset / "ireland.parquet", index=False)
    messages = [issue.message for issue in qa.check_dataset(dataset, raw) if issue.level == "error"]
    assert any("window" in message for message in messages)


def test_provenance_version_disagreeing_with_the_registry_is_an_error(tmp_path: Path) -> None:
    dataset, raw = _frames(tmp_path)
    path = dataset / "provenance.json"
    provenance = json.loads(path.read_text(encoding="utf-8"))
    provenance["version"] = "9.9.9"
    path.write_text(json.dumps(provenance), encoding="utf-8")
    messages = [issue.message for issue in qa.check_dataset(dataset, raw) if issue.level == "error"]
    assert any("version" in message for message in messages)


def test_missing_permalink_is_only_a_warning(tmp_path: Path) -> None:
    dataset, raw = _frames(tmp_path)
    path = dataset / "provenance.json"
    provenance = json.loads(path.read_text(encoding="utf-8"))
    provenance["regions"]["ireland"].pop("permalink")
    path.write_text(json.dumps(provenance), encoding="utf-8")
    issues = qa.check_dataset(dataset, raw)
    assert [issue for issue in issues if issue.level == "error"] == []
    assert any("permalink" in issue.message for issue in issues)


def test_unknown_dataset_folder_is_an_error(tmp_path: Path) -> None:
    dataset = tmp_path / "processed" / "not_in_registry"
    dataset.mkdir(parents=True)
    (dataset / "provenance.json").write_text("{}", encoding="utf-8")
    messages = [issue.message for issue in qa.check_dataset(dataset, tmp_path / "raw")]
    assert "dataset_id is not in the registry" in messages


def test_regenerate_reports_a_mismatched_series(tmp_path: Path) -> None:
    dataset, raw = _frames(tmp_path)
    frame = pd.read_parquet(dataset / "ireland.parquet")
    frame["value"] = 99.0
    frame.to_parquet(dataset / "ireland.parquet", index=False)

    scratch = tmp_path / "scratch"
    scratch.mkdir()
    issues = qa.regenerate(dataset, raw, scratch)
    assert any("values differ" in issue.message for issue in issues)


def test_main_exits_non_zero_when_a_dataset_is_broken(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dataset, raw = _frames(tmp_path)
    (dataset / "provenance.json").unlink()
    assert qa.main(["--processed", str(tmp_path / "processed"), "--raw", str(raw)]) == 1
    assert "no provenance.json" in capsys.readouterr().out


def test_canonical_box_ignores_number_formatting() -> None:
    assert qa.canonical_box("-10.5,51.4,-6,55.4") == qa.canonical_box("-10.5,51.4,-6.0,55.4")
