"""Parse Giovanni area-averaged time-series CSV exports.

A Giovanni export is not a clean CSV: it opens with a comment block, may carry a
parameter/unit block above the table, and can end with source notes. Only the
date column and one value column are used here, and anything that does not parse
as a monthly row is skipped, so a new export shape cannot silently corrupt a
series.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

MONTH_RE = re.compile(r"^(\d{4})-(\d{1,2})(?:-\d{1,2})?(?:[ T].*)?$")

MISSING_TOKENS = {
    "",
    "-999",
    "-999.0",
    "-9999",
    "-9999.0",
    "nan",
    "na",
    "n/a",
    "none",
    "null",
}

DATE_HEADERS = {"month", "date", "time", "datetime", "year-month", "ym", "yyyy-mm"}

UNIT_KEYS = {"unit", "units"}


class GiovanniParseError(ValueError):
    """Raised when a Giovanni CSV has no usable date/value table."""


def _cells(line: str) -> list[str]:
    return [cell.strip().strip('"').strip() for cell in line.split(",")]


def _find_header(lines: list[str]) -> tuple[int, int, int]:
    """Return (line index, date column, value column) of the table header."""
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        cells = _cells(line)
        for column, cell in enumerate(cells):
            lowered = cell.lower()
            if lowered in DATE_HEADERS or lowered.startswith(("month", "date")):
                value_column = next(
                    (later for later in range(column + 1, len(cells)) if cells[later]), None
                )
                if value_column is None:
                    raise GiovanniParseError(f"header on line {index + 1} has no value column")
                return index, column, value_column
    raise GiovanniParseError("no date/value header found in Giovanni CSV")


def parse_giovanni_csv(text: str) -> pd.DataFrame:
    """Parse a Giovanni time-series CSV into ``timestamp`` and ``value`` columns."""
    lines = text.splitlines()
    header_line, date_column, value_column = _find_header(lines)

    rows: list[tuple[pd.Timestamp, float | None]] = []
    for line in lines[header_line + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        cells = _cells(line)
        if len(cells) <= value_column:
            continue
        match = MONTH_RE.match(cells[date_column])
        if not match:
            continue  # a unit row, a note, or a footer
        year, month = int(match.group(1)), int(match.group(2))
        if not 1 <= month <= 12:
            continue
        raw = cells[value_column].replace(",", "")
        if raw.lower() in MISSING_TOKENS:
            value: float | None = None
        else:
            try:
                value = float(raw)
            except ValueError:
                continue
        rows.append((pd.Timestamp(year=year, month=month, day=1), value))

    if not rows:
        raise GiovanniParseError("no monthly rows recovered from Giovanni CSV")

    frame = pd.DataFrame(rows, columns=["timestamp", "value"])
    frame = frame.drop_duplicates(subset="timestamp", keep="last")
    return frame.sort_values("timestamp").reset_index(drop=True)


def read_giovanni_csv(path: str | Path) -> pd.DataFrame:
    """Read and parse a Giovanni CSV file from disk."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return parse_giovanni_csv(text)


def declared_unit(text: str) -> str | None:
    """Return the unit Giovanni printed above the table, if it printed one.

    Exports carry a ``Unit,K`` (or ``Units: mm/month``) line above the header.
    That line is the only evidence of what the numbers in the file actually are,
    so the builder compares it against the registry instead of trusting either
    side alone: a silently pre-converted export must not be converted twice.
    """
    for line in text.splitlines()[:40]:
        stripped = line.strip()
        if not stripped:
            continue
        key, separator, value = stripped.partition(",")
        if not separator:
            key, separator, value = stripped.partition(":")
        if separator and key.strip().strip('"').strip().lower() in UNIT_KEYS:
            unit = value.strip().strip('"').strip()
            return unit or None
    return None


def read_giovanni_unit(path: str | Path) -> str | None:
    """Read the declared unit from a Giovanni CSV file, if present."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return declared_unit(text)
