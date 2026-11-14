"""Build the References list from provenance (doc 11 §8, NAS-43).

The submission has to cite every dataset it used, and the citation must be the
one that was actually fetched — not a hand-typed URL that drifts from what the
pipeline wrote. So the dataset citations are generated from `provenance.json`,
the software list from `pyproject.toml`, and only the papers the code actually
implements are named by hand.

    uv run python -m pipeline.references data/processed > docs/references.md

Doc 11 §8 asks for datasets, libraries, tools and papers. It also says, through
this ticket, to cite AppEEARS/KNMI/CDO/POWER *only if used* — so anything we did
not use is listed explicitly under "Not used" rather than padded into the list.
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

REGION_NAMES = {
    "ireland": "Ireland",
    "iberia": "Iberia",
    "sahel": "Sahel",
    "nw_india": "NW India",
    "us_southwest": "US Southwest",
}

# Papers whose methods this repo actually implements, via `analysis/` and
# `pipeline.eda`. Kept short and checkable: every line maps to code.
LITERATURE = [
    "Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*, 13(3), 245–259. "
    "— the Mann–Kendall trend test.",
    "Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau. "
    "*Journal of the American Statistical Association*, 63(324), 1379–1389. — Sen's slope.",
    "Hamed, K. H., & Rao, A. R. (1998). A modified Mann–Kendall trend test for autocorrelated "
    "data. *Journal of Hydrology*, 204, 182–196. — the Hamed–Rao variance correction used "
    "on monthly series.",
]

UNUSED = [
    ("KNMI Climate Explorer", "no cross-check was run; that stretch row was never started"),
    ("SeaWiFS", "no ocean-colour variable is in the Lineup"),
    ("AppEEARS", "the NDVI stretch row was never started"),
    ("NOAA CDO", "no station data was pulled — the token never arrived"),
    ("NASA POWER", "used once as a cross-check for T2M, then superseded by the Giovanni export; "
                   "the committed series do not come from it"),
]

TEMPLATE = (
    "NASA GES DISC Giovanni, *{product}*, {short_name} v{version}, "
    "{region} ({box}), {start}–{end}, accessed {accessed}. {permalink}"
)


def short_name(product: str) -> str:
    """The dataset short name, which provenance keeps inside the product label."""
    if "(" in product and product.rstrip().endswith(")"):
        return product.rsplit("(", 1)[1].rstrip(")").strip()
    return product


def citations(provenance: dict) -> list[str]:
    """One citation per region, using each region's own box, window and permalink."""
    lines: list[str] = []
    product = provenance.get("product", "unknown product")
    name = short_name(product)
    version = provenance.get("version", "?")
    accessed = provenance.get("access_date", "?")
    for region_id, region in sorted((provenance.get("regions") or {}).items()):
        box = region.get("requested_box") or region.get("analyzable_region") or "?"
        start = str(region.get("period_start", provenance.get("period_start", "?")))[:7]
        end = str(region.get("period_end", provenance.get("period_end", "?")))[:7]
        permalink = region.get("permalink") or provenance.get("doi_or_url") or ""
        lines.append(
            TEMPLATE.format(
                product=product.split(" (")[0].rstrip(","),
                short_name=name,
                version=version,
                region=REGION_NAMES.get(region_id, region_id.replace("_", " ").title()),
                box=box,
                start=start,
                end=end,
                accessed=accessed,
                permalink=permalink,
            ).strip()
        )
    return lines


def tools(pyproject: Path) -> list[str]:
    """The software the repo declares, with the versions it pins."""
    if not pyproject.exists():
        return []
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    found = []
    for requirement in data.get("project", {}).get("dependencies", []):
        found.append(f"`{requirement}`")
    for group in data.get("dependency-groups", {}).values():
        for requirement in group:
            found.append(f"`{requirement}` (development)")
    return found


def render(paths: list[Path], pyproject: Path = Path("pyproject.toml")) -> str:
    """Markdown References section: datasets, tools, papers, and what was not used."""
    seen: dict[str, None] = {}
    for path in paths:
        provenance = json.loads(path.read_text(encoding="utf-8"))
        for line in citations(provenance):
            seen.setdefault(line, None)

    data_block = "\n".join(f"- {line}" for line in seen) or "- (no processed series yet)"
    declared = tools(pyproject)
    tool_block = "\n".join(f"- {tool}" for tool in declared) or "- (no dependencies declared)"
    paper_block = "\n".join(f"- {entry}" for entry in LITERATURE)
    unused_block = "\n".join(f"- **{name}** — not cited: {reason}." for name, reason in UNUSED)

    return (
        "# References\n\n"
        "<!-- Generated from data/processed/*/provenance.json and pyproject.toml by "
        "`uv run python -m pipeline.references` — do not edit by hand. -->\n\n"
        "## Data\n\n"
        f"{data_block}\n\n"
        "## Software\n\n"
        f"{tool_block}\n\n"
        "## Methods\n\n"
        f"{paper_block}\n\n"
        "## Not used, therefore not cited\n\n"
        f"{unused_block}\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="References list from provenance files")
    parser.add_argument("directory", type=Path, nargs="?", default=Path("data/processed"))
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    args = parser.parse_args(argv)

    paths = sorted(args.directory.glob("*/provenance.json"))
    print(render(paths, args.pyproject), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
