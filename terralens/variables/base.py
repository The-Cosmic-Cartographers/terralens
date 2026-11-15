"""One class per dataset; subclasses only describe loading and metadata."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .. import cache
from .._registry import VARIABLES
from ..trends import TrendResult

BASELINE = (1991, 2020)


class Variable:
    """A single variable for a single region.

    ``load`` reads the committed parquet, ``trend`` calls the shared analysis,
    and everything else is presentation. Subclasses set ``variable_id`` and
    ``alias``; nothing else should need overriding except ``annual_agg``.
    """

    variable_id: str = ""
    alias: str = ""
    annual_agg: str | None = None

    def __init__(self, region) -> None:
        self.region = region
        self.spec = VARIABLES[self.variable_id]
        self._frame: pd.DataFrame | None = None

    # -- metadata -----------------------------------------------------------
    @property
    def dataset_id(self) -> str:
        return self.spec.dataset_id

    @property
    def units(self) -> str:
        return self.spec.output_unit

    @property
    def resolution(self) -> str:
        return self.spec.spatial_resolution

    @property
    def label(self) -> str:
        from .._meta import LABELS

        return LABELS.get(self.variable_id, self.variable_id)

    @property
    def citation(self) -> str:
        return (
            f"{self.spec.product}, version {self.spec.version} "
            f"(dataset {self.spec.dataset_id}); accessed from the committed TerraLens data tree"
        )

    # -- data ---------------------------------------------------------------
    def load(self) -> pd.DataFrame:
        """Monthly values as ``date, value, coverage_fraction``."""
        if self._frame is None:
            path = cache.processed_path(self.dataset_id, self.region.region_id)
            if not path.exists():
                raise FileNotFoundError(
                    f"no processed series for {self.variable_id!r} in {self.region.region_id!r} "
                    f"(expected {path}). Available variables: "
                    f"{', '.join(self.region.available_variables()) or 'none'}"
                )
            frame = pd.read_parquet(path)
            frame = frame.rename(columns={"timestamp": "date"})
            frame["date"] = pd.to_datetime(frame["date"])
            frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
            if "coverage_fraction" in frame:
                frame["coverage_fraction"] = pd.to_numeric(
                    frame["coverage_fraction"], errors="coerce"
                ).fillna(1.0)
            else:
                frame["coverage_fraction"] = 1.0
            self._frame = frame.sort_values("date").reset_index(drop=True)[
                ["date", "value", "coverage_fraction"]
            ]
        return self._frame.copy()

    def _annual_aggregate(self) -> str:
        if self.annual_agg is not None:
            return self.annual_agg
        from .._meta import ANNUAL_AGG

        return ANNUAL_AGG.get(self.variable_id, "mean")

    def annual(self) -> tuple[tuple[int, float | None], ...]:
        """One value per complete calendar year; ``None`` when months are missing."""
        frame = self.load()
        aggregate = self._annual_aggregate()
        out: list[tuple[int, float | None]] = []
        for year, group in frame.groupby(frame["date"].dt.year, sort=True):
            if len(group) < 12 or group["value"].isna().any():
                out.append((int(year), None))
            else:
                total = float(group["value"].sum() if aggregate == "sum" else group["value"].mean())
                out.append((int(year), total))
        return tuple(out)

    # -- statistics ---------------------------------------------------------
    def trend(self, *, baseline: tuple[int, int] = BASELINE) -> TrendResult:
        """Run ``terralens._stats.analyze_series`` and wrap the result.

        This is the only place the package touches statistics, and it calls the
        same function that builds the app's results.
        """
        from .. import _stats
        from .._meta import ANNUAL_AGG, PRODUCT_TYPE, SLOPE_BASE_UNIT

        frame = self.load()
        rows = [
            {
                "year": int(stamp.year),
                "month": int(stamp.month),
                "value": None if pd.isna(value) else float(value),
                "coverage_fraction": float(coverage),
            }
            for stamp, value, coverage in zip(
                frame["date"], frame["value"], frame["coverage_fraction"], strict=True
            )
        ]
        aggregate = (
            ANNUAL_AGG.get(self.variable_id, "mean") if self.annual_agg is None else self.annual_agg
        )
        payload = _stats.analyze_series(
            rows,
            dataset_id=self.dataset_id,
            variable_id=self.variable_id,
            region_id=self.region.region_id,
            unit=self.units,
            # The slope is fitted to the annual aggregate, so a summed variable's slope
            # is an annual total per year, the same label the app shows.
            unit_per_year=f"{SLOPE_BASE_UNIT.get(self.variable_id, self.units)}/yr",
            product_type=PRODUCT_TYPE.get(self.variable_id, "reanalysis"),
            window=(self.spec.start_year, self.spec.end_year),
            annual_agg=aggregate,
            baseline=baseline,
            bh_family=None,
        )
        coverage = self.region.cells(self.variable_id)
        if coverage.warn:
            payload["caveats"] = list(payload.get("caveats") or []) + [
                f"region resolution: {coverage.detail}"
            ]
        return TrendResult.from_analysis(
            payload,
            label=self.label,
            citation=self.citation,
            annual=self.annual(),
        )

    def anomalies(self, baseline: tuple[int, int] = BASELINE) -> pd.DataFrame:
        """Monthly anomalies against a per-calendar-month climatology."""
        frame = self.load()
        years = frame["date"].dt.year
        window = frame[(years >= baseline[0]) & (years <= baseline[1])]
        source = window if not window.empty else frame
        climatology = source.groupby(source["date"].dt.month)["value"].mean()
        out = frame.copy()
        out["anomaly"] = out["value"] - out["date"].dt.month.map(climatology)
        return out[["date", "value", "anomaly"]]

    def seasonal(self) -> pd.DataFrame:
        """Mean anomaly by calendar month (a climatology, not a trend)."""
        anomalies = self.anomalies()
        anomalies["month"] = anomalies["date"].dt.month
        return (
            anomalies.groupby("month", as_index=False)
            .agg(mean_value=("value", "mean"), mean_anomaly=("anomaly", "mean"))
            .reset_index(drop=True)
        )

    # -- presentation -------------------------------------------------------
    def plot(self, ax=None):
        from .. import plots

        return plots.plot_variable(self, ax=ax)

    def refresh(self) -> None:
        """Not part of the offline POC; point at the real pull command."""
        raise NotImplementedError(
            "refresh() is not shipped in the offline POC. Pull the series first with "
            "`python -m pipeline.pull --variable-id <id> --region-id <region>`, "
            "then reload the package."
        )

    def __repr__(self) -> str:
        return f"Variable({self.variable_id!r}, region={self.region.region_id!r})"


def annual_sd(values: Any) -> float:
    """Standard deviation of the non-null annual values, used in quick checks."""
    clean = [value for value in values if value is not None]
    return float(np.std(clean, ddof=1)) if len(clean) > 1 else float("nan")
