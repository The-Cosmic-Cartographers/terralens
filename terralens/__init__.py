"""TerraLens: honest regional trends from NASA Earth data.

    >>> import terralens as tl
    >>> tl.list_regions()
    ['iberia', 'ireland', 'nw_south_asia', 'sahel', 'us_southwest']
    >>> ireland = tl.ireland
    >>> ireland.summary()

Numbers come from the committed series under ``data/processed`` and the same
statistics as the app (``terralens._stats``). Nothing is downloaded on import.
"""

from __future__ import annotations

from typing import Any

from . import regions as _regions

__version__ = "0.1.3"


def list_regions() -> list[str]:
    """Region ids that ship with the POC."""
    return _regions.region_ids()


def region(name: str) -> _regions.Region:
    """One region by id, with a suggestion when the name is misspelled."""
    return _regions.get_region(name)


def compare(a: str, b: str, variables: list[str] | None = None):
    """Compare two regions; see ``terralens._compare.compare``."""
    from ._compare import compare as _compare

    return _compare(a, b, variables)


def adjust_bh(results):
    """Apply Benjamini-Hochberg across a declared family of results.

    Pass several ``TrendResult`` objects that answer one question; the q-value
    is stored on each returned result. See ``terralens._adjust.adjust_bh``.
    """
    from ._adjust import adjust_bh as _adjust_bh

    return _adjust_bh(results)


def __getattr__(name: str) -> Any:
    """``tl.ireland`` works without a separate import."""
    if name.startswith("_"):
        raise AttributeError(name)
    try:
        return region(name)
    except _regions.UnknownRegionError as error:
        raise AttributeError(str(error)) from None


__all__ = ["list_regions", "region", "compare", "adjust_bh", "__version__"]
