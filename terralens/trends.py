"""The result object.

Every number here comes from ``analysis.stats.analyze_series`` — the same
function that builds the app's results. This module maps that payload into an
object; it does not compute a second trend, and it never invents a p-value.

One difference from the app is deliberate and must stay visible: a single
series is a family of one test, so its p-value is unadjusted. The Lineup and
compare views apply Benjamini–Hochberg across several tests, so their adjusted
p can be larger. ``family_size`` and ``warnings`` say so.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

UNADJUSTED_NOTE = (
    "single-series p is unadjusted (family size 1); the app's Lineup and compare "
    "views apply Benjamini-Hochberg across several tests, so their adjusted p can differ"
)


@dataclass(frozen=True)
class TrendResult:
    """A trend with its uncertainty, period and citation."""

    variable_id: str
    region_id: str
    dataset_id: str
    label: str
    unit: str
    per_decade: float | None
    confidence_interval_95: tuple[float, float] | None
    p_value: float | None
    n_obs: int
    period: tuple[int, int]
    direction: str
    method: str
    verdict: str
    caveats: tuple[str, ...]
    family_size: int
    citation: str
    adjusted_p_value: float | None = None
    annual: tuple[tuple[int, float | None], ...] | None = field(default=None, repr=False)

    # -- construction -------------------------------------------------------
    @classmethod
    def from_analysis(
        cls,
        payload: dict[str, Any],
        *,
        label: str,
        citation: str,
        annual: tuple[tuple[int, float | None], ...] | None = None,
    ) -> TrendResult:
        """Map the schema-2 payload from ``analysis.stats.analyze_series``."""
        slope = payload.get("sen_slope_per_year")
        ci = payload.get("confidence_interval_95")
        ci_pair: tuple[float, float] | None = None
        if ci and ci[0] is not None and ci[1] is not None:
            ci_pair = (float(ci[0]) * 10.0, float(ci[1]) * 10.0)
        start = payload.get("period_start")
        end = payload.get("period_end")
        period = (int(start), int(end)) if start is not None and end is not None else (0, 0)
        unit = (payload.get("unit_per_year") or "/yr").removesuffix("/yr")
        return cls(
            variable_id=payload["variable_id"],
            region_id=payload["region_id"],
            dataset_id=payload["dataset_id"],
            label=label,
            unit=unit,
            per_decade=None if slope is None else float(slope) * 10.0,
            confidence_interval_95=ci_pair,
            p_value=None if payload.get("p_value") is None else float(payload["p_value"]),
            n_obs=int(payload.get("observation_count") or 0),
            period=period,
            direction=payload.get("trend_direction", "withheld"),
            method=payload.get("method", ""),
            verdict=payload.get("verdict", "not_enough_data"),
            caveats=tuple(payload.get("caveats") or ()),
            family_size=1,
            citation=citation,
            annual=annual,
        )

    # -- derived ------------------------------------------------------------
    @property
    def slope_per_year(self) -> float | None:
        return None if self.per_decade is None else self.per_decade / 10.0

    @property
    def warnings(self) -> tuple[str, ...]:
        if self.family_size <= 1:
            return self.caveats + (UNADJUSTED_NOTE,)
        if self.adjusted_p_value is None:
            return self.caveats + (
                f"withheld from Benjamini-Hochberg adjustment (family size {self.family_size})",
            )
        return self.caveats + (
            f"p adjusted with Benjamini-Hochberg across {self.family_size} tests",
        )

    def _p_text(self) -> str:
        adjusted = self.family_size > 1 and self.adjusted_p_value is not None
        p_value = self.adjusted_p_value if adjusted else self.p_value
        if p_value is None:
            return "no p-value"
        label = "q" if adjusted else "p"
        return f"{label}<0.001" if p_value < 0.001 else f"{label}={p_value:.3f}"

    def __repr__(self) -> str:
        if self.per_decade is None:
            reason = self.caveats[0] if self.caveats else "not enough data"
            return f"{self.label} ({self.region_id}): {reason}"
        if self.direction == "increasing":
            lead = "Warming" if self.variable_id == "t2m" else "Increasing"
        elif self.direction == "decreasing":
            lead = "Cooling" if self.variable_id == "t2m" else "Decreasing"
        else:
            lead = "No clear trend"
        return (
            f"{self.label}: {lead} {self.per_decade:+.2f} {self.unit}/decade, "
            f"{self._p_text()}, {self.period[0]}-{self.period[1]}"
        )

    # -- serialisation ------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "variable_id": self.variable_id,
            "region_id": self.region_id,
            "dataset_id": self.dataset_id,
            "label": self.label,
            "unit": self.unit,
            "per_decade": self.per_decade,
            "slope_per_year": self.slope_per_year,
            "confidence_interval_95": list(self.confidence_interval_95 or ()) or None,
            "p_value": self.p_value,
            "adjusted_p_value": self.adjusted_p_value,
            "n_obs": self.n_obs,
            "period_start": self.period[0],
            "period_end": self.period[1],
            "direction": self.direction,
            "method": self.method,
            "verdict": self.verdict,
            "caveats": list(self.caveats),
            "family_size": self.family_size,
            "citation": self.citation,
            "warnings": list(self.warnings),
        }

    def to_json(self, path: str | Path | None = None) -> str:
        text = json.dumps(self.to_dict(), indent=2)
        if path is not None:
            Path(path).write_text(text + "\n", encoding="utf-8")
        return text

    def to_csv(self, path: str | Path | None = None) -> str:
        buffer = io.StringIO()
        row = self.to_dict()
        flat = {
            key: ("" if value is None else json.dumps(value) if isinstance(value, list) else value)
            for key, value in row.items()
        }
        writer = csv.DictWriter(buffer, fieldnames=list(flat))
        writer.writeheader()
        writer.writerow(flat)
        text = buffer.getvalue()
        if path is not None:
            Path(path).write_text(text, encoding="utf-8")
        return text

    # -- plotting -----------------------------------------------------------
    def plot(self, ax=None):
        """Annual series with the fitted Sen line; returns the axes."""
        from . import plots

        return plots.plot_trend(self, ax=ax)
