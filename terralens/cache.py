"""Where TerraLens finds its data.

The repository's own ``data/`` directory *is* the cache: the pull pipeline
writes ``data/processed/<dataset_id>/<region_id>.parquet`` and the analysis
writes ``data/results/``. Nothing is duplicated into the package, so the
numbers in a notebook are the numbers the app serves.

``TERRALENS_DATA`` points the whole package at another checkout (a frozen
snapshot, a test fixture, a colleague's copy). No download happens here.
"""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
DEFAULT_DATA_ROOT = REPO_ROOT / "data"
#: A wheel installs the committed series next to the code, because there is no
#: repository checkout to point at.
BUNDLED_DATA_ROOT = PACKAGE_ROOT / "_data"


def data_root() -> Path:
    """Root of the data tree.

    Order: ``TERRALENS_DATA`` override, then a repository checkout's ``data/``,
    then the series bundled inside the installed package.
    """
    override = os.environ.get("TERRALENS_DATA")
    if override:
        return Path(override).expanduser().resolve()
    if (DEFAULT_DATA_ROOT / "processed").is_dir():
        return DEFAULT_DATA_ROOT
    return BUNDLED_DATA_ROOT


def processed_path(dataset_id: str, region_id: str) -> Path:
    """Path of one monthly series."""
    return data_root() / "processed" / dataset_id / f"{region_id}.parquet"


def results_path(*parts: str) -> Path:
    """Path inside ``data/results`` (lineup, windows, or a dataset folder)."""
    return data_root().joinpath("results", *parts)


def has_series(dataset_id: str, region_id: str) -> bool:
    """True when the processed series exists, without opening it."""
    return processed_path(dataset_id, region_id).exists()
