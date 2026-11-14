"""Read-only access to the data/ folder (processed series and results).

Layout, relative to the data root (the same for data/ and data/fixtures/):

    data_version.txt
    catalogue.json
    regions.json
    metadata/<dataset_id>.json
    processed/<dataset_id>/provenance.json
"""

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.config import DATA_VERSION_FALLBACK
from app.models import CatalogueItem, Metadata, Provenance, Region


class DataUnavailable(Exception):
    """A data file is missing or does not validate (HTTP 503 data_unavailable)."""

    def __init__(self, relative_path: str, reason: str) -> None:
        super().__init__(f"{relative_path}: {reason}")
        self.relative_path = relative_path
        self.reason = reason


class DatasetNotFound(Exception):
    """The dataset_id is not in the catalogue (HTTP 404 dataset_not_found)."""

    def __init__(self, dataset_id: str) -> None:
        super().__init__(dataset_id)
        self.dataset_id = dataset_id


class DataStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _read_json(self, relative_path: str) -> Any:
        path = self.root / relative_path
        if not path.is_file():
            raise DataUnavailable(relative_path, "file is missing")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise DataUnavailable(relative_path, f"not valid JSON ({error.msg})") from error

    def _validated(self, relative_path: str, validate):
        payload = self._read_json(relative_path)
        try:
            return validate(payload)
        except ValidationError as error:
            raise DataUnavailable(relative_path, "does not match the contract") from error

    def data_version(self) -> str:
        path = self.root / "data_version.txt"
        if not path.is_file():
            return DATA_VERSION_FALLBACK
        return path.read_text(encoding="utf-8").strip() or DATA_VERSION_FALLBACK

    def catalogue(self) -> list[CatalogueItem]:
        adapter = TypeAdapter(list[CatalogueItem])
        return self._validated("catalogue.json", adapter.validate_python)

    def regions(self) -> list[Region]:
        adapter = TypeAdapter(list[Region])
        return self._validated("regions.json", adapter.validate_python)

    def metadata(self, dataset_id: str) -> Metadata:
        if dataset_id not in {item.dataset_id for item in self.catalogue()}:
            raise DatasetNotFound(dataset_id)
        provenance = self._validated(
            f"processed/{dataset_id}/provenance.json", lambda p: Provenance(**p)
        )
        return self._validated(
            f"metadata/{dataset_id}.json",
            lambda extras: Metadata(dataset_id=dataset_id, provenance=provenance, **extras),
        )
