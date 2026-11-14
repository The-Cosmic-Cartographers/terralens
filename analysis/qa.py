"""Scientific QA of the generated results (NAS-48).

Checks the artefacts in data/results/ against the rules the team agreed in
docs 10 and 11 — the checks a human would otherwise do by eye, done every time
the pipeline runs. Writes docs/qa-report.md and exits non-zero on any failure.

What this can check: every number, verdict, period, unit, ranking, window and
withheld row in the generated files.
What this cannot check: the words on the frontend and the project page, because
those screens do not exist yet. The report lists them as open items rather than
pretending they passed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from analysis import stats as tl
from analysis.run import REPO_ROOT, RESULTS
from pipeline.registry import VARIABLES

REPORT = REPO_ROOT / "docs" / "qa-report.md"


class Checks:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.rows.append((name, bool(passed), detail))

    @property
    def failed(self) -> list[tuple[str, bool, str]]:
        return [row for row in self.rows if not row[1]]


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_trends(checks: Checks) -> int:
    count = 0
    for path in sorted(RESULTS.glob("*/trends.json")):
        for row in _load(path):
            count += 1
            label = f"{row['region_id']}/{row['variable_id']}"
            spec = VARIABLES.get(row["variable_id"])
            withheld = row["trend_direction"] == "withheld"

            if spec is not None:
                period_detail = (
                    f"{row['period_start']}..{row['period_end']} "
                    f"vs {spec.start_year}-{spec.end_year}"
                )
                checks.add(
                    f"{label}: period inside the registered window",
                    int(row["period_start"][:4]) >= spec.start_year
                    and int(row["period_end"][:4]) <= spec.end_year,
                    period_detail,
                )
                checks.add(
                    f"{label}: unit matches the registry",
                    row["unit_per_year"] == f"{spec.output_unit}/yr",
                    row["unit_per_year"],
                )

            if withheld:
                checks.add(
                    f"{label}: withheld row carries no statistics",
                    row["sen_slope_per_year"] is None
                    and row["p_value"] is None
                    and row["adjusted_p_value"] is None
                    and row["confidence_interval_95"] is None,
                )
                checks.add(
                    f"{label}: withheld row explains itself",
                    bool(row["withheld_reason"]),
                    row["withheld_reason"] or "missing reason",
                )
                checks.add(
                    f"{label}: withheld row is labelled not_enough_data",
                    row["verdict"] == "not_enough_data" and not row["significant_at_0_05"],
                )
                checks.add(
                    f"{label}: withheld row has no detectability",
                    row["detect_years"] is None and row["effect_size_swings"] is None,
                )
                checks.add(
                    f"{label}: withheld row has no D25 diagnostics",
                    row.get("change_point") is None and row.get("seasonal_slopes") is None,
                )
                continue

            p, adj = row["p_value"], row["adjusted_p_value"]
            low, high = row["confidence_interval_95"]
            checks.add(
                f"{label}: adjusted p is not below raw p",
                adj >= p - 1e-12,
                f"{p:.3e} -> {adj:.3e}",
            )
            checks.add(f"{label}: CI is ordered", low <= high, f"{low:.4f}..{high:.4f}")
            checks.add(
                f"{label}: significant flag agrees with adjusted p",
                row["significant_at_0_05"] == (adj < 0.05),
                f"adj={adj:.4f}",
            )
            checks.add(
                f"{label}: verdict label agrees with adjusted p",
                row["verdict"] == tl.verdict_from_p(adj, withheld=False),
                row["verdict"],
            )
            checks.add(
                f"{label}: direction agrees with the slope sign",
                (
                    row["trend_direction"] == "increasing" and row["sen_slope_per_year"] > 0
                )
                or (
                    row["trend_direction"] == "decreasing" and row["sen_slope_per_year"] < 0
                )
                or row["trend_direction"] == "no_significant_trend",
                f"{row['trend_direction']} slope={row['sen_slope_per_year']:+.4f}",
            )
            checks.add(
                f"{label}: detectability only on non-significant rows",
                (row["detect_years"] is None) if row["significant_at_0_05"] else True,
            )
            checks.add(
                f"{label}: observation count is plausible",
                0 < row["observation_count"] <= 12 * 100,
                str(row["observation_count"]),
            )
            checks.add(
                f"{label}: coverage is a fraction",
                0.0 <= row["mean_coverage_fraction"] <= 1.0,
                f"{row['mean_coverage_fraction']:.3f}",
            )

            # --- D25 diagnostics: shown, descriptive, contract-shaped --------
            change_point = row.get("change_point")
            seasons = row.get("seasonal_slopes")
            start_year = int(row["period_start"][:4])
            end_year = int(row["period_end"][:4])
            checks.add(
                f"{label}: change point falls inside the period",
                change_point is not None
                and start_year <= change_point["change_point_year"] <= end_year,
                str(change_point and change_point["change_point_year"]),
            )
            checks.add(
                f"{label}: change point stays a diagnostic",
                change_point is not None
                and (change_point["p_value"] < 0.05 and row["verdict"] != "significant")
                == ("level_shift_detected" in row["caveats"]),
            )
            checks.add(
                f"{label}: one slope for each season",
                seasons is not None and set(seasons) == {"DJF", "MAM", "JJA", "SON"},
                ",".join(sorted(seasons)) if seasons else "missing",
            )
    return count


def check_lineups(checks: Checks) -> int:
    count = 0
    for path in sorted(RESULTS.glob("lineup/*.json")):
        lineup = _load(path)
        region = lineup["region_id"]
        checks.add(
            f"lineup {region}: family names the region",
            lineup["bh_family"] == f"lineup:{region}",
            lineup["bh_family"],
        )
        rows = lineup["rows"]
        checks.add(f"lineup {region}: has at least one row", len(rows) >= 1, str(len(rows)))

        for row in rows:
            count += 1
            trend = row["trend"]
            checks.add(
                f"lineup {region}/{row['variable_id']}: row and trend agree",
                (row["dataset_id"], row["variable_id"])
                == (trend["dataset_id"], trend["variable_id"])
                and row["product_type"] == trend["product_type"]
                and trend["bh_family"] == lineup["bh_family"],
            )
            checks.add(
                f"lineup {region}/{row['variable_id']}: row period matches its trend",
                (row["period_start"], row["period_end"])
                == (trend["period_start"], trend["period_end"]),
            )
            checks.add(
                f"lineup {region}/{row['variable_id']}: sparkline is present",
                len(row["sparkline"]) > 0,
                str(len(row["sparkline"])),
            )
            checks.add(
                f"lineup {region}/{row['variable_id']}: plain-language definition",
                bool(row["definition"].strip()) and len(row["definition"]) >= 15,
                row["definition"][:40],
            )

        ranked = sorted(
            rows,
            key=lambda r: (
                1 if r["trend"]["adjusted_p_value"] is None else 0,
                r["trend"]["adjusted_p_value"]
                if r["trend"]["adjusted_p_value"] is not None
                else 1.0,
                -(r["trend"]["effect_size_swings"] or 0.0),
            ),
        )
        checks.add(
            f"lineup {region}: rows are ranked by evidence",
            [r["variable_id"] for r in rows] == [r["variable_id"] for r in ranked],
            "->".join(r["variable_id"] for r in rows),
        )
    return count


def check_windows(checks: Checks) -> int:
    count = 0
    for path in sorted(RESULTS.glob("windows/*/*.json")):
        payload = _load(path)
        region = payload["region_id"]
        minimum = payload["min_window_years"]
        windows = payload["windows"]
        count += len(windows)

        checks.add(f"windows {region}: minimum length is 10", minimum == 10, str(minimum))
        checks.add(f"windows {region}: file is not empty", len(windows) > 0, str(len(windows)))

        pairs = {(w["start"], w["end"]) for w in windows}
        checks.add(
            f"windows {region}: no duplicate start/end pairs",
            len(pairs) == len(windows),
            f"{len(pairs)} unique of {len(windows)}",
        )
        bad_length = [w for w in windows if w["end"] - w["start"] + 1 < minimum]
        checks.add(f"windows {region}: every window spans the minimum", not bad_length,
                   f"{len(bad_length)} short")

        bad_ci = [
            w
            for w in windows
            if w["confidence_interval_95"]
            and w["confidence_interval_95"][0] > w["confidence_interval_95"][1]
        ]
        checks.add(f"windows {region}: CIs are ordered", not bad_ci, f"{len(bad_ci)} bad")

        bad_p = [
            w
            for w in windows
            if w["adjusted_p_value"] is not None
            and w["p_value"] is not None
            and w["adjusted_p_value"] < w["p_value"] - 1e-12
        ]
        checks.add(
            f"windows {region}: adjusted p never below raw p", not bad_p, f"{len(bad_p)} bad"
        )

        bad_verdict = [
            w for w in windows if w["verdict"] != tl.verdict_from_p(w["adjusted_p_value"], False)
        ]
        checks.add(f"windows {region}: verdicts match adjusted p", not bad_verdict,
                   f"{len(bad_verdict)} bad")
    return count


def check_evidence_page(checks: Checks) -> None:
    page = REPO_ROOT / "docs" / "sensitivity-notes.md"
    checks.add("evidence page exists", page.exists(), str(page.relative_to(REPO_ROOT)))
    if page.exists():
        text = page.read_text(encoding="utf-8")
        checks.add("evidence page names its generator", "analysis.sensitivity" in text)
        checks.add("evidence page has no placeholder brackets", "[region]" not in text)


def build_report(checks: Checks, trend_count: int, lineup_count: int, window_count: int) -> str:
    passed = sum(1 for _, ok, _ in checks.rows if ok)
    total = len(checks.rows)
    lines = [
        "# Scientific QA report (NAS-48)",
        "",
        "Generated by `python -m analysis.qa`. The automated half of the sign-off: every",
        "number, verdict, period, unit, ranking and window in `data/results/` checked",
        "against the agreed rules.",
        "",
        f"**{passed}/{total} checks passed.** "
        f"Artefacts: {trend_count} trend rows, {lineup_count} lineup rows, {window_count} windows.",
        "",
        "## Results",
        "",
        "| Check | Result | Detail |",
        "| -- | -- | -- |",
    ]
    for name, ok, detail in checks.rows:
        lines.append(f"| {name} | {'PASS' if ok else '**FAIL**'} | {detail} |")

    lines += [
        "",
        "## Not covered by the automated pass",
        "",
        "These need a human and, in two cases, screens that do not exist yet:",
        "",
        "* **Frontend copy** — verdict pills, method box, limitations panel, error and "
        "empty states. Blocked on the screens (NAS-31 to NAS-35).",
        "* **Project page numbers** — every figure on the submission form has to be "
        "re-read from `data/results/` (NAS-39, NAS-40).",
        "* **Wording** — the say/don't-say table in `docs/methodology.md` §8 has to be "
        "applied by eye to every sentence a judge reads.",
        "* **Provenance** — dataset versions and access dates in `provenance.json` "
        "against the actual Giovanni exports (NAS-41).",
        "",
        "## Sign-off",
        "",
        "Automated pass: "
        + ("**clean**" if not checks.failed else f"**{len(checks.failed)} failures**")
        + ".",
        "",
        "Full scientific sign-off cannot be given until the displayed copy exists. A green",
        "run here means the numbers are internally correct and consistent with the contract,",
        "not that the words around them are right.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    checks = Checks()
    trend_count = check_trends(checks)
    lineup_count = check_lineups(checks)
    window_count = check_windows(checks)
    check_evidence_page(checks)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        build_report(checks, trend_count, lineup_count, window_count), encoding="utf-8"
    )

    passed = sum(1 for _, ok, _ in checks.rows if ok)
    print(f"wrote {REPORT.relative_to(REPO_ROOT)}")
    print(f"{passed}/{len(checks.rows)} checks passed")
    for name, _ok, detail in checks.failed:
        print(f"  FAIL {name} [{detail}]")
    return 1 if checks.failed else 0


if __name__ == "__main__":
    sys.exit(main())
