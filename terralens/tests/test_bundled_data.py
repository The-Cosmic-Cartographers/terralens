"""The wheel carries its own copy of the series; it must not drift from the repo's."""

from __future__ import annotations

from pathlib import Path

import pytest

from terralens import cache
from terralens._registry import VARIABLES

REPO_PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"
BUNDLED_PROCESSED = cache.BUNDLED_DATA_ROOT / "processed"
MVP = [spec for variable_id, spec in VARIABLES.items() if variable_id != "no2"]


@pytest.mark.skipif(not REPO_PROCESSED.is_dir(), reason="no repository checkout")
@pytest.mark.parametrize("spec", MVP, ids=lambda spec: spec.dataset_id)
def test_bundled_series_match_the_repository_series(spec):
    bundled = sorted((BUNDLED_PROCESSED / spec.dataset_id).glob("*.parquet"))
    assert len(bundled) == 5, f"{spec.dataset_id}: expected five regions"
    for path in bundled:
        source = REPO_PROCESSED / spec.dataset_id / path.name
        assert path.read_bytes() == source.read_bytes(), (
            f"{path.name} differs from data/processed; re-copy the series into "
            "terralens/_data/processed"
        )


def test_the_bundle_holds_only_the_five_mvp_datasets():
    on_disk = {path.name for path in BUNDLED_PROCESSED.iterdir() if path.is_dir()}
    assert on_disk == {spec.dataset_id for spec in MVP}
