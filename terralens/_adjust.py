"""Benjamini-Hochberg adjustment for an explicit family of trends."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from . import _stats
from .trends import TrendResult


def adjust_bh(results: Iterable[TrendResult]) -> list[TrendResult]:
    """Adjust a declared family of results with Benjamini-Hochberg.

    The caller decides what belongs to one family. Results are returned in the
    same order; ``p_value`` keeps the raw value and ``adjusted_p_value`` receives
    the q-value. Withheld results (``p_value is None``) are not tested, stay in
    the list, and are not counted in the family.
    """
    items = list(results)
    if not all(isinstance(item, TrendResult) for item in items):
        raise TypeError("adjust_bh expects an iterable of TrendResult objects")

    tested = [(index, item) for index, item in enumerate(items) if item.p_value is not None]
    family_size = len(tested)
    if family_size < 2:
        return items

    q_values = _stats.benjamini_hochberg_adjusted(
        [item.p_value for _, item in tested]
    )
    q_by_index = {
        index: float(q)
        for (index, _), q in zip(tested, q_values, strict=True)
    }

    adjusted: list[TrendResult] = []
    for index, item in enumerate(items):
        if item.p_value is None:
            adjusted.append(replace(item, family_size=family_size))
            continue

        q_value = q_by_index[index]
        verdict = _stats.verdict_from_p(q_value, withheld=False)
        if verdict == "significant" and item.per_decade is not None:
            direction = "increasing" if item.per_decade > 0 else "decreasing"
        elif verdict == "significant":
            direction = item.direction
        else:
            direction = "no_significant_trend"

        adjusted.append(
            replace(
                item,
                adjusted_p_value=q_value,
                family_size=family_size,
                verdict=verdict,
                direction=direction,
            )
        )
    return adjusted
