"""Build the References list from provenance (doc 11 §8, NAS-43).

The submission has to cite every dataset it used, and the citation must be the
one that was actually fetched — not a hand-typed URL that drifts from what the
pipeline wrote. So the list is generated from `provenance.json` rather than
maintained by hand:

    uv run python -m pipeline.references data/processed > docs/references.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REGION_NAMES = {
    "ireland": "Ireland",
    "iberia": "Iberia",
    "sahel": "Sahel",
    "nw_india": "NW India",
    "us_southwest": "US Southwest",
}

TEMPLATE = (
    "NASA GES DISC Giovanni, *{product}*, {short_name} v{version}, "
    "{region} ({box}), {start}–{end}, accessed {accessed}."
)


def short_name(product: str) -> str:
    """The dataset short name, which provenance keeps inside the product label."""
    if "(" in product and product.rstrip().endswith(")"):
        return product.rsplit("(", 1)[1].rstrip(")").strip()
    return product


def citations(provenance: dict) -> list[str]:
    """One citation per region, using each region's own box and window."""
    lines: list[str] = []
    product = provenance.get("product", "unknown product")
    name = short_name(product)
    version = provenance.get("version", "?")
    accessed = provenance.get("access_date", "?")
    for region_id, region in sorted((provenance.get("regions") or {}).items()):
        box = region.get("requested_box") or region.get("analyzable_region") or "?"
        start = str(region.get("period_start", provenance.get("period_start", "?")))[:7]
        end = str(region.get("period_end", provenance.get("period_end", "?")))[:7]
        lines.append(
            TEMPLATE.format(
                product=product.split(" (")[0],
                short_name=name,
                version=version,
                region=REGION_NAMES.get(region_id, region_id.replace("_", " ").title()),
                box=box,
                start=start,
                end=end,
                accessed=accessed,
            )
        )
    return lines


def render(paths: list[Path]) -> str:
    """Markdown References section, de-duplicated and stable across runs."""
    seen: dict[str, None] = {}
    for path in paths:
        provenance = json.loads(path.read_text(encoding="utf-8"))
        for line in citations(provenance):
            seen.setdefault(line, None)
    body = "\n".join(f"- {line}" for line in seen) or "- (no processed series yet)"
    return (
        "# References\n\n"
        "<!-- Generated from data/processed/*/provenance.json by "
        "`uv run python -m pipeline.references` — do not edit by hand. -->\n\n"
        "## Data\n\n"
        f"{body}\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="References list from provenance files")
    parser.add_argument("directory", type=Path, nargs="?", default=Path("data/processed"))
    args = parser.parse_args(argv)

    paths = sorted(args.directory.glob("*/provenance.json"))
    print(render(paths), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
