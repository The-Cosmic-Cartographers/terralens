"""Read-only access to the data/ folder (processed series and results).

Layout, relative to the data root (the same for data/ and data/fixtures/):

    data_version.txt
    catalogue.json
    regions.json
    metadata/<dataset_id>.json
    processed/<dataset_id>/provenance.json
    processed/<dataset_id>/<region_id>.parquet
    results/lineup/<region_id>.json
    results/windows/<dataset_id>/<region_id>.json
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import TypeAdapter

from app.config import DATA_VERSION_FALLBACK
from app.models import (
    CatalogueItem,
    Lineup,
    Metadata,
    Provenance,
    Region,
    SeriesResponse,
    SeriesRow,
    TrendResult,
    Windows,
)


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


class RegionNotFound(Exception):
    """The region_id is not in regions.json (HTTP 404 region_not_found)."""

    def __init__(self, region_id: str) -> None:
        super().__init__(region_id)
        self.region_id = region_id


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

    def _validated(self, relative_path: str, validate: Callable[[Any], Any]) -> Any:
        payload = self._read_json(relative_path)
        try:
            return validate(payload)
        except (ValueError, TypeError) as error:  # pydantic's ValidationError is a ValueError
            raise DataUnavailable(relative_path, "does not match the contract") from error

    def _require_region(self, region_id: str) -> None:
        if region_id not in {region.region_id for region in self.regions()}:
            raise RegionNotFound(region_id)

    def _require_dataset(self, dataset_id: str) -> None:
        if dataset_id not in {item.dataset_id for item in self.catalogue()}:
            raise DatasetNotFound(dataset_id)

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
        self._require_dataset(dataset_id)
        provenance = self._validated(
            f"processed/{dataset_id}/provenance.json", lambda p: Provenance(**p)
        )
        return self._validated(
            f"metadata/{dataset_id}.json",
            lambda extras: Metadata(dataset_id=dataset_id, provenance=provenance, **extras),
        )

    def series(self, region_id: str, dataset_id: str) -> SeriesResponse:
        self._require_region(region_id)
        self._require_dataset(dataset_id)
        relative = f"processed/{dataset_id}/{region_id}.parquet"
        path = self.root / relative
        if not path.is_file():
            raise DataUnavailable(relative, "file is missing")
        try:
            records = pq.read_table(path).to_pylist()
        except (pa.ArrowException, OSError) as error:
            raise DataUnavailable(relative, "not a readable Parquet file") from error
        try:
            rows = [SeriesRow(**record) for record in records]
            if not rows:
                raise ValueError("the file has no rows")
            return SeriesResponse(
                dataset_id=dataset_id,
                variable_id=rows[0].variable_id,
                region_id=region_id,
                unit=rows[0].unit,
                rows=rows,
            )
        except (ValueError, TypeError) as error:
            raise DataUnavailable(relative, "does not match the contract") from error

    def lineup(self, region_id: str) -> Lineup:
        self._require_region(region_id)

        def validate(payload: Any) -> Lineup:
            lineup = Lineup(**payload)
            if lineup.region_id != region_id:
                raise ValueError("the file belongs to another region")
            return lineup

        return self._validated(f"results/lineup/{region_id}.json", validate)

    def trend(self, region_id: str, dataset_id: str) -> TrendResult:
        """The lineup-family result, so the detail card matches the Lineup verdict."""
        self._require_dataset(dataset_id)
        lineup = self.lineup(region_id)
        for row in lineup.rows:
            if row.dataset_id == dataset_id:
                return row.trend
        raise DataUnavailable(
            f"results/lineup/{region_id}.json", f"no lineup row for dataset {dataset_id}"
        )

    def windows(self, region_id: str, dataset_id: str) -> Windows:
        self._require_region(region_id)
        self._require_dataset(dataset_id)

        def validate(payload: Any) -> Windows:
            windows = Windows(**payload)
            if (windows.dataset_id, windows.region_id) != (dataset_id, region_id):
                raise ValueError("the file belongs to another dataset or region")
            return windows

        return self._validated(f"results/windows/{dataset_id}/{region_id}.json", validate)
