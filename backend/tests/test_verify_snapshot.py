"""The snapshot verifier catches contract breaks and SAMPLE data before they ship."""

import json
import shutil
from pathlib import Path

import pytest

from app.export import export
from app.verify_snapshot import main, verify

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"


@pytest.fixture(scope="module")
def good(tmp_path_factory):
    out = tmp_path_factory.mktemp("snapshot")
    export(FIXTURES, out, allow_sample=True)
    return out


@pytest.fixture
def copy(good, tmp_path):
    out = tmp_path / "snapshot"
    shutil.copytree(good, out)
    return out


def test_a_good_snapshot_is_clean_when_sample_is_allowed(good):
    assert verify(good, allow_sample=True) == []


def test_sample_data_is_reported_by_default(good):
    problems = verify(good)
    assert any("data_version" in p for p in problems)
    assert any("contains SAMPLE data" in p for p in problems)


def test_a_missing_file_is_reported(copy):
    (copy / "lineup" / "ireland.json").unlink()
    assert "lineup/ireland.json: file is missing" in verify(copy, allow_sample=True)


def test_a_file_that_breaks_the_contract_is_reported(copy):
    path = copy / "trend" / "sample_t2m" / "ireland.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["verdict"] = "significant"
    payload["adjusted_p_value"] = 0.9
    path.write_text(json.dumps(payload), encoding="utf-8")
    problems = verify(copy, allow_sample=True)
    assert problems == [
        "trend/sample_t2m/ireland.json: does not match the contract (ValidationError)"
    ]


def test_a_file_at_the_wrong_path_is_reported(copy):
    shutil.copy(copy / "windows/sample_t2m/iberia.json", copy / "windows/sample_t2m/ireland.json")
    problems = verify(copy, allow_sample=True)
    assert any(p.startswith("windows/sample_t2m/ireland.json") for p in problems)


def test_an_empty_folder_is_not_clean(tmp_path):
    assert verify(tmp_path, allow_sample=True)


def test_cli_exit_codes(good, capsys):
    assert main([str(good)]) == 1
    assert "NOT clean" in capsys.readouterr().err
    assert main([str(good), "--allow-sample"]) == 0
    assert "is clean" in capsys.readouterr().out
