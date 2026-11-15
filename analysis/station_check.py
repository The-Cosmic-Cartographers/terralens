"""Ground-station direction check against NOAA CDO monthly summaries (NAS-44).

For Ireland and the US Southwest this compares the reanalysis rows (MERRA-2 air
temperature and precipitation) with long station records from NOAA's Climate Data
Online (dataset GSOM, global summary of the month). It is a direction check, not a
validation of the numbers: stations measure a point, the model a box average.

    NCDC_CDO=<token> PYTHONPATH=backend:. python -m analysis.station_check

The token is read from the environment and never written anywhere. Output:
`docs/station-check.md`. Stations are every GSOM station inside the region box with a
record from the mid-1980s or earlier into 2024 or later and at least 80% of months
present in 1981-2025 (air temperature) or 1980-2025 (precipitation).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date

import numpy as np
import pandas as pd

from analysis import stats as tl
from analysis.run import BASELINE, REPO_ROOT
from pipeline.regions import load_regions

BASE = "https://www.ncei.noaa.gov/cdo-web/api/v2"
DOC = REPO_ROOT / "docs" / "station-check.md"
REGIONS = ("ireland", "us_southwest")
MIN_COVERAGE = 0.8
MAX_STATIONS = 12

# variable -> (CDO datatype, our dataset, our window, annual aggregation, unit label)
TARGETS = {
    "air temperature": ("TAVG", "merra2_m2tmnxslv", (1981, 2025), "mean", "°C per decade"),
    "precipitation": (
        "PRCP",
        "merra2_m2tmnxflx_prectotcorr_v5_12_4",
        (1980, 2025),
        "sum",
        "mm (annual total) per decade",
    ),
}


def token() -> str:
    value = os.environ.get("NCDC_CDO", "").strip()
    if not value:
        raise SystemExit("set NCDC_CDO to a NOAA CDO token (not stored in the repo)")
    return value


def get(path: str, params: dict[str, object], key: str) -> dict:
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={"token": key})
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read().decode("utf-8")
            time.sleep(0.25)  # CDO allows 5 requests per second
            return json.loads(payload) if payload.strip() else {}
        except Exception:  # noqa: BLE001 - retry any transient failure
            time.sleep(1.5 * (attempt + 1))
    return {}


def stations_in_box(box: dict, datatype: str, key: str) -> list[dict]:
    extent = f"{box['south']},{box['west']},{box['north']},{box['east']}"
    found: list[dict] = []
    offset = 1
    while True:
        page = get(
            "stations",
            {
                "datasetid": "GSOM",
                "datatypeid": datatype,
                "extent": extent,
                "limit": 1000,
                "offset": offset,
                "sortfield": "datacoverage",
                "sortorder": "desc",
            },
            key,
        )
        found.extend(page.get("results", []))
        total = page.get("metadata", {}).get("resultset", {}).get("count", 0)
        offset += 1000
        if offset > total:
            return found


def station_series(station_id: str, datatype: str, years: tuple[int, int], key: str) -> pd.Series:
    rows: list[dict] = []
    start = years[0]
    while start <= years[1]:
        end = min(start + 9, years[1])
        page = get(
            "data",
            {
                "datasetid": "GSOM",
                "stationid": station_id,
                "datatypeid": datatype,
                "startdate": f"{start}-01-01",
                "enddate": f"{end}-12-31",
                "units": "metric",
                "limit": 1000,
            },
            key,
        )
        rows.extend(page.get("results", []))
        start = end + 1
    if not rows:
        return pd.Series(dtype=float)
    frame = pd.DataFrame(rows)
    frame["t"] = pd.to_datetime(frame["date"]).dt.to_period("M").dt.to_timestamp()
    return frame.groupby("t")["value"].mean().astype(float)


def trend(series: pd.Series, window: tuple[int, int], agg: str) -> dict:
    full = pd.date_range(f"{window[0]}-01-01", f"{window[1]}-12-01", freq="MS")
    series = series.reindex(full)
    rows = [
        {
            "year": stamp.year,
            "month": stamp.month,
            "value": None if pd.isna(value) else float(value),
            "coverage_fraction": 1.0,
        }
        for stamp, value in series.items()
    ]
    result = tl.analyze_series(
        rows,
        dataset_id="station",
        variable_id="x",
        region_id="x",
        unit="x",
        product_type="reanalysis",
        window=window,
        baseline=BASELINE,
        annual_agg=agg,
        bh_family="station",
    )
    return result


def model_series(dataset: str, region: str, window: tuple[int, int]) -> pd.Series:
    frame = pd.read_parquet(REPO_ROOT / "data" / "processed" / dataset / f"{region}.parquet")
    frame["t"] = pd.to_datetime(frame["timestamp"])
    series = frame.set_index("t")["value"].astype(float)
    return series[(series.index.year >= window[0]) & (series.index.year <= window[1])]


def anomalies(series: pd.Series) -> pd.Series:
    return series - series.groupby(series.index.month).transform("mean")


def main() -> int:
    key = token()
    regions = load_regions()
    lines = [
        "# Ground-station direction check (NAS-44)",
        "",
        f"Generated {date.today().isoformat()} by `python -m analysis.station_check` from NOAA "
        "Climate Data Online (GSOM monthly summaries). A **direction check**: stations measure "
        "a point, the model a box average, so slopes are not expected to match, only their sign "
        "and the broad significance. The same statistics (seasonal Mann-Kendall with Hamed-Rao "
        "correction, Sen's slope) are used for the stations and the model.",
        "",
    ]
    summary: list[tuple[str, str, int, int, str, str]] = []
    for region in REGIONS:
        box = regions[region]
        lines += [f"## {box['name']}", ""]
        for label, (datatype, dataset, window, agg, unit) in TARGETS.items():
            candidates = [
                s
                for s in stations_in_box(box, datatype, key)
                if s["mindate"] <= f"{window[0] + 4}-12-31"
                and s["maxdate"] >= f"{window[1] - 1}-01-01"
            ][: MAX_STATIONS * 2]
            kept: list[tuple[dict, pd.Series, dict]] = []
            for station in candidates:
                series = station_series(station["id"], datatype, window, key)
                span = pd.date_range(f"{window[0]}-01-01", f"{window[1]}-12-01", freq="MS")
                coverage = series.reindex(span).notna().mean() if len(series) else 0.0
                if coverage < MIN_COVERAGE:
                    continue
                kept.append((station, series, trend(series, window, agg)))
                if len(kept) >= MAX_STATIONS:
                    break
            model = model_series(dataset, region, window)
            model_trend = trend(model, window, agg)
            lines += [
                f"### {label.capitalize()} ({window[0]}-{window[1]})",
                "",
                "| Station | Months present | Slope per decade | "
                "p (serial-correlation corrected) | Direction |",
                "| -- | -- | -- | -- | -- |",
            ]
            signs: list[int] = []
            for station, series, result in kept:
                slope = result["sen_slope_per_year"] * 10
                direction = "increasing" if slope > 0 else "decreasing"
                signs.append(1 if slope > 0 else -1)
                present = int(
                    series.reindex(
                        pd.date_range(f"{window[0]}-01-01", f"{window[1]}-12-01", freq="MS")
                    )
                    .notna()
                    .sum()
                )
                lines.append(
                    f"| {station['name'].title()} ({station['id'].split(':')[1]}) | {present} | "
                    f"{slope:+.3f} | {result['p_value']:.3g} | {direction} |"
                )
            model_slope = model_trend["sen_slope_per_year"] * 10
            lines += [
                f"| **Model box (MERRA-2)** | {len(model)} | **{model_slope:+.3f}** | "
                f"**{model_trend['p_value']:.3g}** | "
                f"**{'increasing' if model_slope > 0 else 'decreasing'}** |",
                "",
            ]
            agree = sum(1 for sign in signs if sign == (1 if model_slope > 0 else -1))
            if kept:
                composite = pd.concat([anomalies(s) for _, s, _ in kept], axis=1, sort=True).mean(
                    axis=1
                )
                joined = pd.concat([composite, anomalies(model)], axis=1, join="inner").dropna()
                corr = float(np.corrcoef(joined.iloc[:, 0], joined.iloc[:, 1])[0, 1])
                snotel = sum(1 for station, _, _ in kept if station["id"].startswith("GHCND:USS"))
                mix = (
                    f" {snotel} of the {len(kept)} stations are SNOTEL mountain sites, which sit "
                    "higher and wetter than the box average."
                    if snotel
                    else ""
                )
                lines += [
                    f"Units: {unit}. {agree} of {len(kept)} stations have the same direction as "
                    f"the model box. Correlation of monthly anomalies between the mean of the "
                    f"stations and the model box: {corr:.2f}.{mix}",
                    "",
                ]
                summary.append((box["name"], label, agree, len(kept), f"{corr:.2f}", unit))
            else:
                lines += ["No station passed the coverage rule.", ""]
                summary.append((box["name"], label, 0, 0, "n/a", unit))
    lines += [
        "## Summary",
        "",
        "| Region | Variable | Stations agreeing in direction | "
        "Anomaly correlation (station mean vs model) |",
        "| -- | -- | -- | -- |",
    ]
    for name, label, agree, total, corr, _unit in summary:
        lines.append(f"| {name} | {label} | {agree} of {total} | {corr} |")
    lines += [
        "",
        "Data: NOAA National Centers for Environmental Information, Climate Data Online, dataset "
        "GSOM (Global Summary of the Month). Queried with a personal API token that is not "
        "stored in this repository.",
        "",
    ]
    DOC.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {DOC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
