"""Compare two regions honestly.

The table always appears; the ordering is only described as supported when the
95 % intervals do not overlap. That is a deliberate refusal, not a bug.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

import pandas as pd

from .trends import TrendResult
from .variables import VARIABLE_CLASSES

UNADJUSTED_NOTE = (
    "single-series p-values are unadjusted (family size 1); the app applies "
    "Benjamini-Hochberg across its Lineup and compare families"
)


def intervals_overlap(
    first: tuple[float, float] | None, second: tuple[float, float] | None
) -> bool:
    """True when two 95 % intervals share any value."""
    if not first or not second:
        return False
    return max(first[0], second[0]) <= min(first[1], second[1])


@dataclass
class Comparison:
    """Two regions, one table, and the caveats that belong beside it."""

    region_a: str
    region_b: str
    variable_ids: tuple[str, ...]
    table: pd.DataFrame
    ranking: pd.DataFrame
    notes: tuple[str, ...]
    _trends: dict[str, tuple[TrendResult, TrendResult]] = field(
        default_factory=dict, repr=False
    )

    def __str__(self) -> str:
        lines = []
        for row in self.table.itertuples(index=False):
            lines.append(
                f"{row.label}: {self.region_a} {row.region_a_per_decade:+.2f} "
                f"{row.unit}/decade vs {self.region_b} {row.region_b_per_decade:+.2f} "
                f"{row.unit}/decade; faster in {row.faster_region}."
            )
        lines.extend(self.notes)
        return "\n".join(lines)

    def plot(self):
        """One overlay panel per compared variable; returns the figure."""
        from . import plots

        plt = plots._pyplot()
        figure, axes = plt.subplots(
            len(self.variable_ids),
            1,
            figsize=(7, 2.8 * len(self.variable_ids)),
            squeeze=False,
        )
        for ax, alias in zip(axes[:, 0], self.variable_ids, strict=True):
            trend_a, trend_b = self._trends[alias]
            for trend, label, colour in (
                (trend_a, self.region_a, "#d95c43"),
                (trend_b, self.region_b, "#4a6fa5"),
            ):
                if not trend.annual:
                    continue
                years = [year for year, value in trend.annual if value is not None]
                values = [value for _, value in trend.annual if value is not None]
                ax.plot(years, values, color=colour, linewidth=1.6, label=label)
            ax.set_title(trend_a.label, loc="left")
            ax.set_ylabel(trend_a.unit)
            ax.legend(frameon=False)
            ax.grid(alpha=0.3)
        figure.tight_layout()
        return figure


def compare(
    region_a,
    region_b,
    variables: Iterable[str] | None = None,
) -> Comparison:
    """Compare two regions over the variables both of them have.

    ``variables`` accepts aliases such as ``"temperature"`` or registry ids
    such as ``"t2m"``. Missing data is never filled in: unavailable variables
    are skipped and the notes say which ones, unless the caller asked for one
    explicitly, in which case it raises.
    """
    from .regions import Region, get_region

    first = region_a if isinstance(region_a, Region) else get_region(str(region_a))
    second = region_b if isinstance(region_b, Region) else get_region(str(region_b))

    requested = variables is not None
    aliases = (
        [_resolve_alias(name) for name in variables]
        if variables is not None
        else [alias for alias in VARIABLE_CLASSES if all(
            (first.variables[alias], second.variables[alias])
        )]
    )

    rows: list[dict[str, object]] = []
    notes: list[str] = []
    trends: dict[str, tuple[TrendResult, TrendResult]] = {}
    skipped: list[str] = []

    for alias in aliases:
        missing = [
            region.region_id
            for region in (first, second)
            if not region.variables[alias]
        ]
        if missing:
            if requested:
                raise ValueError(f"{alias!r} has no processed series for {', '.join(missing)}")
            skipped.append(alias)
            continue

        trend_a = getattr(first, alias).trend()
        trend_b = getattr(second, alias).trend()
        if trend_a.per_decade is None or trend_b.per_decade is None:
            skipped.append(alias)
            continue

        if trend_a.period != trend_b.period:
            notes.append(
                f"{alias}: the two series cover different periods "
                f"({trend_a.period[0]}-{trend_a.period[1]} vs "
                f"{trend_b.period[0]}-{trend_b.period[1]}); read the difference with care."
            )
        if intervals_overlap(trend_a.confidence_interval_95, trend_b.confidence_interval_95):
            notes.append(
                f"{alias}: the 95% intervals overlap, so the ordering is not "
                "supported by the intervals."
            )

        faster = first.region_id if trend_a.per_decade > trend_b.per_decade else second.region_id
        rows.append(
            {
                "variable": alias,
                "label": trend_a.label,
                "unit": trend_a.unit,
                "region_a_per_decade": trend_a.per_decade,
                "region_b_per_decade": trend_b.per_decade,
                "difference_per_decade": trend_a.per_decade - trend_b.per_decade,
                "faster_region": faster,
                "p_value_a": trend_a.p_value,
                "p_value_b": trend_b.p_value,
            }
        )
        trends[alias] = (trend_a, trend_b)

    if not rows:
        raise ValueError(
            f"{first.region_id} and {second.region_id} share no variable with data"
        )
    if skipped:
        notes.append(f"Skipped (no series or no verdict): {', '.join(skipped)}.")
    notes.append(UNADJUSTED_NOTE)

    table = pd.DataFrame(rows)
    ranking = (
        table[["variable", "faster_region", "region_a_per_decade", "region_b_per_decade"]]
        .rename(columns={"faster_region": "faster"})
        .reset_index(drop=True)
    )
    return Comparison(
        region_a=first.region_id,
        region_b=second.region_id,
        variable_ids=tuple(table["variable"]),
        table=table,
        ranking=ranking,
        notes=tuple(notes),
        _trends=trends,
    )


def _resolve_alias(name: str) -> str:
    if name in VARIABLE_CLASSES:
        return name
    for alias, cls in VARIABLE_CLASSES.items():
        if cls.variable_id == name:
            return alias
    raise ValueError(
        f"unknown variable {name!r}; use one of {', '.join(VARIABLE_CLASSES)} "
        f"or the registry ids {', '.join(cls.variable_id for cls in VARIABLE_CLASSES.values())}"
    )
