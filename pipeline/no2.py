"""Daily OMI NO2 for the two city boxes, one OPeNDAP subset per day (NAS-27).

The Lineup's NO2 row is a *daily* product, not a monthly one: OMNO2d reports one
cloud-screened retrieval per day and simply has no value where the sky was not
clear. The pipeline therefore stores the daily series and lets `pipeline.omi`
reduce it with the D22 ten-valid-day rule.

Routes that do not work for V004, and are therefore not used here:

* **Harmony** rejects the collection with ``Coverages were not found for the
  provided variables``; the service registers no coverage for OMNO2d.
* **Giovanni time series** knows the product only as V003. The V004 data id
  returns ``Data parameter is invalid``, and mixing V003 into a V004 series is
  not allowed.
* **Giovanni SSW** answers ``dataSetNotConfigured`` for the V004 product.
* **S3 direct** issues temporary credentials but the role is not authorised to
  read ``gesdisc-cumulus-prod-protected``.
* **No-auth / HTTP Basic** both redirect to Earthdata Login.

What does work is the granule-level OPeNDAP service, which serves a NetCDF
subset of any granule to a bearer token. One request per city per day returns
only the box's cells -- 1-3 kB against the 11 MB global granule -- and needs no
redirect handling. That is the route implemented here; the direct HTTPS
full-granule download stays available as the fallback for anything the
subsetter cannot answer.

The footprint rule is the same as everywhere else in the pipeline: only cells
whose *centre* falls inside the registered box are averaged, cosine-latitude
weighted. Verifying that rule on the granule matters here because Dublin's box
is narrower than one 0.25 degree cell, so the intersecting set and the
centre-in-box set are not the same thing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter

from pipeline import build as build_module
from pipeline import omi
from pipeline.regions import load_regions
from pipeline.registry import VARIABLES, Variable

COLLECTION = "C3333493715-GES_DISC"
PRODUCT_DOI = "https://doi.org/10.5067/Aura/OMI/DATA3407"
FIELD_PATH = "/HDFEOS/GRIDS/ColumnAmountNO2/Data_Fields/ColumnAmountNO2TropCloudScreened"
CMR_GRANULES = "https://cmr.earthdata.nasa.gov/search/granules.json"

# OMNO2d is a global 0.25 degree grid whose cell centres start half a step in.
GRID_ORIGIN_LAT = -89.875
GRID_ORIGIN_LON = -179.875
GRID_STEP = 0.25

# Anything at or below this is the product's missing value (-1.2676506e30).
FILL = -1e29

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
CHECKPOINTS = RAW / ".pull"
CHECKPOINT_SECONDS = 20.0
TOKEN_ENV = "EARTHDATA_TOKEN"
UA = "terralens/0.1 (OPeNDAP granule subset)"

_LOCAL = threading.local()


class No2RouteError(RuntimeError):
    """Raised when a day's subset cannot be read after the retry cap."""


def session() -> requests.Session:
    """One keep-alive session per worker; this network resets fresh handshakes."""
    current = getattr(_LOCAL, "session", None)
    if current is None:
        current = requests.Session()
        current.mount("https://", HTTPAdapter(pool_connections=8, pool_maxsize=8, max_retries=0))
        current.headers.update({"User-Agent": UA, "Connection": "keep-alive"})
        _LOCAL.session = current
    return current


def index_range(box: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    """Return the inclusive ``y0, y1, x0, x1`` cell range whose centres are in the box.

    The product's grid is fixed, so the range is geometry, not a request: a box
    whose edge falls between two centres keeps only the centre that is inside.
    """
    west, south, east, north = box
    y0 = math.ceil((south - GRID_ORIGIN_LAT) / GRID_STEP - 1e-9)
    y1 = math.floor((north - GRID_ORIGIN_LAT) / GRID_STEP + 1e-9)
    x0 = math.ceil((west - GRID_ORIGIN_LON) / GRID_STEP - 1e-9)
    x1 = math.floor((east - GRID_ORIGIN_LON) / GRID_STEP + 1e-9)
    if y0 > y1 or x0 > x1:
        raise ValueError(f"box {box} contains no 0.25 degree cell centre")
    return y0, y1, x0, x1


def series_box_string(box: tuple[float, float, float, float]) -> str:
    """The requested box as W,S,E,N, the order every other provenance entry uses."""
    return f"{box[0]},{box[1]},{box[2]},{box[3]}"


def cell_extent(y0: int, y1: int, x0: int, x1: int) -> str:
    """The W,S,E,N extent of the cells actually averaged, for provenance."""
    south = GRID_ORIGIN_LAT + GRID_STEP * y0
    north = GRID_ORIGIN_LAT + GRID_STEP * y1
    west = GRID_ORIGIN_LON + GRID_STEP * x0
    east = GRID_ORIGIN_LON + GRID_STEP * x1
    # same W,S,E,N order as requested_box, so the two can be read side by side
    return f"{west:.2f},{south:.2f},{east:.2f},{north:.2f}"


def subset_url(base: str, y0: int, y1: int, x0: int, x1: int) -> str:
    """The granule URL plus the constraint that selects only this box."""
    return f"{base}.nc?{FIELD_PATH}[{y0}:1:{y1}][{x0}:1:{x1}]"


def parse_subset(payload: bytes, y0: int, y1: int, x0: int, x1: int) -> float | None:
    """Cosine-latitude area mean of one subset, or None when every cell is fill.

    A day with no clearance is *absent*, not zero: returning None is what makes
    ``pipeline.omi`` count valid days instead of averaging holes.
    """
    from scipy.io import netcdf_file

    with netcdf_file(io.BytesIO(payload), mmap=False) as handle:
        fields = [
            variable
            for variable in handle.variables.values()
            if len(getattr(variable, "dimensions", ())) == 2
        ]
        if len(fields) != 1:
            raise ValueError(f"expected one 2-D field, found {len(fields)}")
        field = fields[0]
        data = np.array(field[:], dtype="float64")
        attributes = field._attributes
        fill = float(attributes.get("_FillValue", FILL))
        scale = float(attributes.get("scale_factor", 1.0))
        offset = float(attributes.get("add_offset", 0.0))

    expected = (y1 - y0 + 1, x1 - x0 + 1)
    if data.shape != expected:
        raise ValueError(f"subset has shape {data.shape}, expected {expected}")

    valid = np.isfinite(data) & (data > fill) & (data > FILL)
    if not valid.any():
        return None
    lat = GRID_ORIGIN_LAT + GRID_STEP * np.arange(y0, y1 + 1)
    weights = np.cos(np.deg2rad(lat))[:, None]
    weight_sum = float(np.where(valid, weights, 0.0).sum())
    if weight_sum == 0:
        return None
    weighted = np.where(valid, (data * scale + offset) * weights, 0.0)
    return float(weighted.sum()) / weight_sum


def request(
    url: str, *, headers: dict[str, str] | None = None, attempts: int = 6, timeout: int = 60
):
    """GET with a short backoff; 4xx answers are permanent and are not retried."""
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            response = session().get(url, headers=headers or {}, timeout=timeout)
            if response.status_code in (400, 401, 403, 404):
                raise No2RouteError(f"HTTP {response.status_code} for {url[:120]}")
            if response.status_code != 200:
                raise requests.HTTPError(f"HTTP {response.status_code}")
            return response
        except No2RouteError:
            raise
        except Exception as error:  # noqa: BLE001 - a reset connection is the norm here
            last = error
            time.sleep(min(0.2 * 2**attempt, 3.0))
    assert last is not None
    raise last


def fetch_day(
    base: str, token: str, y0: int, y1: int, x0: int, x1: int, *, attempts: int = 6
) -> float | None:
    """Download and reduce one day's subset; raises when the response is not NetCDF."""
    response = request(
        subset_url(base, y0, y1, x0, x1),
        headers={"Authorization": "Bearer " + token},
        attempts=attempts,
    )
    if not response.content.startswith(b"CDF"):
        raise No2RouteError(f"not NetCDF: {response.content[:40]!r}")
    return parse_subset(response.content, y0, y1, x0, x1)


def granule_index(
    first_day: dt.date,
    last_day: dt.date,
    *,
    cache_path: Path | None = None,
    refresh: bool = False,
    say=print,
) -> dict[str, str]:
    """Map every day in the window to its granule's OPeNDAP URL, via CMR.

    The collection covers the window except for 34 days of known Aura outages;
    those days are simply absent from the map, and the caller reports them as
    gaps rather than treating them as a failed download.
    """
    if cache_path and cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("window") == [first_day.isoformat(), last_day.isoformat()]:
            say(f"    granule index: {len(cached['days'])} days from {cache_path.name}")
            return dict(cached["days"])

    days: dict[str, str] = {}
    page = 1
    while True:
        url = (
            f"{CMR_GRANULES}?collection_concept_id={COLLECTION}"
            f"&temporal={first_day.isoformat()}T00:00:00Z,{last_day.isoformat()}T23:59:59Z"
            f"&page_size=2000&page_num={page}"
        )
        response = request(url, attempts=6, timeout=120)
        entries = response.json()["feed"]["entry"]
        for entry in entries:
            day = entry["time_start"][:10]
            link = next(
                (
                    item["href"]
                    for item in entry.get("links", [])
                    if f"/collections/{COLLECTION}/granules/" in item.get("href", "")
                ),
                None,
            )
            if link:
                days[day] = link
        if len(entries) < 2000:
            break
        page += 1

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "window": [first_day.isoformat(), last_day.isoformat()],
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "days": dict(sorted(days.items())),
                },
                indent=0,
            )
            + "\n",
            encoding="utf-8",
        )
    say(f"    granule index: {len(days)} days from CMR")
    return dict(sorted(days.items()))


def wanted_days(first_year: int, last_year: int) -> list[str]:
    """Every calendar day the registry window asks for."""
    day = dt.date(first_year, 1, 1)
    end = dt.date(last_year, 12, 31)
    days: list[str] = []
    while day <= end:
        days.append(day.isoformat())
        day += dt.timedelta(days=1)
    return days


@dataclass
class DaySeries:
    """One city's daily values, checkpointed so a killed run resumes."""

    region_id: str
    box: tuple[float, float, float, float]
    dataset_id: str = "omi_omno2d_v004"
    days: dict[str, float | None] = field(default_factory=dict)
    index: tuple[int, int, int, int] | None = None
    checkpoint_dir: Path = CHECKPOINTS

    @property
    def label(self) -> str:
        return f"no2/{self.region_id}"

    def checkpoint(self) -> Path:
        return self.checkpoint_dir / f"{self.dataset_id}_{self.region_id}.json"

    def load(self) -> None:
        path = self.checkpoint()
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.days = {str(day): value for day, value in payload.get("days", {}).items()}
        raw = payload.get("index")
        self.index = tuple(int(part) for part in raw) if raw else None
        self._check()

    def _check(self) -> None:
        """A checkpoint may only hold numbers; anything else is a writer bug."""
        for day, value in self.days.items():
            if value is not None and not isinstance(value, (int, float)):
                raise TypeError(
                    f"{self.label}: checkpoint value for {day} is "
                    f"{type(value).__name__}, not a number"
                )

    def save(self) -> None:
        self._check()
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint().write_text(
            json.dumps(
                {
                    "region_id": self.region_id,
                    "box": list(self.box),
                    "index": list(self.index) if self.index else None,
                    "days": dict(sorted(self.days.items())),
                },
                indent=0,
            )
            + "\n",
            encoding="utf-8",
        )


def pull_region(
    series: DaySeries,
    granules: dict[str, str],
    token: str,
    *,
    deadline: dt.timedelta | None = None,
    workers: int = 10,
    say=print,
) -> None:
    """Fill one city's daily values from OPeNDAP, saving as it goes."""
    series.load()
    if series.index is None:
        series.index = index_range(series.box)
    y0, y1, x0, x1 = series.index

    wanted = wanted_days(VARIABLES["no2"].start_year, VARIABLES["no2"].end_year)
    pending = [day for day in wanted if day in granules and day not in series.days]
    absent = [day for day in wanted if day not in granules]
    say(
        f"  {series.label}: {len(series.days)} stored, {len(pending)} to fetch, "
        f"{len(absent)} days with no granule"
    )
    if not pending:
        return

    started = time.monotonic()
    last_save = started
    done = 0
    errors: dict[str, str] = {}

    def task(day: str) -> float | None:
        return fetch_day(granules[day], token, y0, y1, x0, x1)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(task, day): day for day in pending}
        for future in as_completed(futures):
            day = futures[future]
            try:
                series.days[day] = future.result()
            except Exception as error:  # noqa: BLE001 - one bad day must not end the run
                errors[day] = f"{type(error).__name__}: {str(error)[:120]}"
            done += 1
            now = time.monotonic()
            if now - last_save >= CHECKPOINT_SECONDS:
                series.save()
                last_save = now
            if done % 500 == 0 or done == len(pending):
                rate = done / max(now - started, 1e-6)
                remaining = len(pending) - done
                say(
                    f"    {done}/{len(pending)} days  {rate:5.1f}/s  "
                    f"eta {remaining / rate / 60:4.1f} min  errors {len(errors)}"
                )
            if deadline is not None and now - started > deadline.total_seconds():
                say(f"    time limit reached after {done} days; rerun to resume")
                for future in futures:
                    future.cancel()
                break

    series.save()
    if errors:
        sample = list(errors.items())[:5]
        say(f"    {len(errors)} days failed, first: {sample}")


def daily_frame(series: DaySeries) -> pd.DataFrame:
    """The stored days that produced a retrieval, as ``timestamp, value`` rows."""
    rows = [
        (pd.Timestamp(day), value)
        for day, value in sorted(series.days.items())
        if value is not None
    ]
    return pd.DataFrame(rows, columns=["timestamp", "value"])


def write_csv(monthly: pd.DataFrame, series: DaySeries, spec: Variable) -> Path:
    """Write the pipeline's raw CSV shape, months only, nulls as blanks."""
    y0, y1, x0, x1 = series.index or index_range(series.box)
    rows = [
        f"{stamp:%Y-%m},{'' if pd.isna(value) else f'{value:.6g}'}"
        for stamp, value in zip(monthly["timestamp"], monthly["value"], strict=True)
    ]
    out = RAW / f"{spec.variable_id}_{series.region_id}.csv"
    header = [
        f"# NASA GES DISC OPeNDAP granule subsets of {COLLECTION} | {spec.product}",
        f"# field {FIELD_PATH} | area mean, centre-in-box cells, cosine-latitude weighted",
        (
            f"# region {series.region_id} box {series_box_string(series.box)}"
            f" | grid rows {y0}-{y1} cols {x0}-{x1} | {len(rows)} months"
        ),
        f"Parameter,{spec.giovanni_variable_id}",
        f"Unit,{spec.native_unit}",
        "Month,Mean",
    ]
    out.write_text("\n".join(header + rows) + "\n", encoding="utf-8")
    return out


def build_series(
    monthly: pd.DataFrame,
    series: DaySeries,
    spec: Variable,
    csv_path: Path,
    out_root: Path,
) -> tuple[Path, Path]:
    """Write the processed parquet with the D22 day counts intact.

    `pipeline.build` is for monthly products and leaves `n_valid_days` null; for
    a daily product that column is the whole point, so the contract frame is
    written here instead of being patched afterwards.
    """
    y0, y1, x0, x1 = series.index or index_range(series.box)
    window = pd.date_range(f"{spec.start_year}-01-01", f"{spec.end_year}-12-01", freq="MS")
    values = (
        monthly.set_index("timestamp")[["value", "n_valid_days", "quality_summary"]]
        .reindex(window)
        .rename_axis("timestamp")
        .reset_index()
    )
    values["n_valid_days"] = values["n_valid_days"].fillna(0).astype("int64")
    values.loc[values["value"].isna(), "value"] = np.nan
    absent = [
        f"0 of {days} days with a valid retrieval" for days in values["timestamp"].dt.days_in_month
    ]
    summary = values["quality_summary"].fillna(pd.Series(absent, index=values.index))

    count = len(values)
    frame = pd.DataFrame(
        {
            "dataset_id": [spec.dataset_id] * count,
            "variable_id": [spec.variable_id] * count,
            "region_id": [series.region_id] * count,
            "timestamp": values["timestamp"].dt.date,
            "value": values["value"].astype("float64"),
            "unit": [spec.output_unit] * count,
            "anomaly": pd.array([pd.NA] * count, dtype="Float64"),
            "valid_cell_count": pd.array([pd.NA] * count, dtype="Int64"),
            "total_cell_count": pd.array([pd.NA] * count, dtype="Int64"),
            "coverage_fraction": pd.array([pd.NA] * count, dtype="Float64"),
            "n_valid_days": values["n_valid_days"].astype("Int64"),
            "quality_summary": summary,
            "source": [f"{spec.product} v{spec.version}".replace(" vv", " v")] * count,
        }
    )

    parquet = build_module.write_series(frame, out_root, spec.dataset_id, series.region_id)
    observed = int(values["value"].notna().sum())
    first, last = values["timestamp"].iloc[0], values["timestamp"].iloc[-1]
    transformations = [
        "one OPeNDAP granule subset per city per day; no full-granule downloads",
        f"subset rows {y0}-{y1}, columns {x0}-{x1} (0.25 degree cells whose centre is in the box)",
        "cosine-latitude weighted area mean per day",
        "missing values and all-fill days kept out of the daily mean",
        "negative daily retrievals retained: the product does not clip retrieval noise",
        f"daily values reduced to months with the D22 rule ({omi.MIN_VALID_DAYS} valid days)",
        f"clipped to the registered window {spec.start_year}-01 to {spec.end_year}-12",
        "missing months kept as null rows",
        "anomaly left null: climatology and anomalies belong to analysis/",
    ]
    provenance = build_module.write_provenance(
        out_root,
        spec.dataset_id,
        {
            "dataset_id": spec.dataset_id,
            "product": spec.product,
            "version": spec.version,
            "doi_or_url": PRODUCT_DOI,
            "access_date": dt.date.today().isoformat(),
            "access_route": "NASA GES DISC OPeNDAP (granule-level NetCDF subset)",
            "variable_field": FIELD_PATH,
            "scale_factor": 1.0,
            "native_unit": spec.native_unit,
            "output_unit": spec.output_unit,
            "spatial_resolution": spec.spatial_resolution,
            "period_start": first.date().isoformat(),
            "period_end": last.date().isoformat(),
            "qa_rules": [
                "OMI OMNO2d V004, daily product, 30% cloud screened",
                "only cells whose centre is inside the registered box",
                (
                    f"monthly value needs at least {omi.MIN_VALID_DAYS} valid days; "
                    "below that it is null"
                ),
                "n_valid_days records the clear days behind each month",
                "coverage_fraction stays null: a daily product has day counts, not cell coverage",
                "no mixing of product versions inside one series",
                "registered variable window, whole calendar years",
                "missing months kept as null rows",
            ],
            "region_source": "Linear doc 11 section 3a NO2 city sub-box",
            "transformations": transformations,
        },
        {
            "region_id": series.region_id,
            "requested_box": series_box_string(series.box),
            "analyzable_region": cell_extent(y0, y1, x0, x1),
            "period_start": first.date().isoformat(),
            "period_end": last.date().isoformat(),
            "giovanni_variable_id": spec.giovanni_variable_id,
            "permalink": f"https://opendap.earthdata.nasa.gov/collections/{COLLECTION}",
            "source_csv": csv_path.name,
            "source_csv_sha256": build_module.sha256_of(csv_path),
            "observations": observed,
            "transformations": transformations,
        },
    )
    return parquet, provenance


def token_from_environment(env: dict[str, str] | None = None) -> str:
    """Read the Earthdata token, declining to guess."""
    import os

    value = (env or os.environ).get(TOKEN_ENV, "").strip()
    if value:
        return value
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
            stripped = line.lstrip("\ufeff").strip()
            if "=" not in stripped or stripped.startswith("#"):
                continue
            key, raw = stripped.split("=", 1)
            if key.strip().lower().replace(" ", "_") in ("earthdata", "earthdata_token"):
                value = raw.strip().strip('"').strip("'")
                if value:
                    return value
    raise RuntimeError(
        f"{TOKEN_ENV} is not set. Export an Earthdata bearer token before running; "
        f"the token is never written to a checkpoint or to provenance."
    )


def run_regions(
    region_ids: list[str] | None,
    *,
    token: str,
    workers: int = 10,
    raw: Path = RAW,
    out: Path = PROCESSED,
    refresh_granules: bool = False,
    build: bool = True,
    deadline: dt.timedelta | None = None,
    say=print,
) -> int:
    """Pull and build every requested city; returns a process exit code."""
    global RAW
    RAW = raw
    regions = load_regions()
    chosen = region_ids or ["dublin_no2", "delhi_no2"]
    spec = VARIABLES["no2"]

    granules = granule_index(
        dt.date(spec.start_year, 1, 1),
        dt.date(spec.end_year, 12, 31),
        cache_path=raw / ".pull" / "omno2d_granules.json",
        refresh=refresh_granules,
        say=say,
    )

    failures: list[str] = []
    for region_id in chosen:
        region = regions[region_id]
        box = (
            float(region["west"]),
            float(region["south"]),
            float(region["east"]),
            float(region["north"]),
        )
        series = DaySeries(
            region_id=region_id,
            box=box,
            checkpoint_dir=raw / ".pull",
        )
        say(f"== no2/{region_id} box {box}")
        pull_region(series, granules, token, deadline=deadline, workers=workers, say=say)

        wanted = wanted_days(spec.start_year, spec.end_year)
        unresolved = [day for day in wanted if day not in series.days and day in granules]
        if unresolved:
            failures.append(f"no2/{region_id}: {len(unresolved)} days unresolved")
            say(f"  no2/{region_id}: {len(unresolved)} days unresolved, not building")
            continue

        daily = daily_frame(series)
        if daily.empty:
            failures.append(f"no2/{region_id}: no valid retrievals at all")
            continue
        monthly = omi.daily_to_monthly(daily)
        csv_path = write_csv(monthly, series, spec)
        say(f"  no2/{region_id}: {len(monthly)} months, {len(daily)} clear days -> {csv_path}")
        if build:
            parquet, _ = build_series(monthly, series, spec, csv_path, out)
            say(f"  no2/{region_id}: -> {parquet}")

    if failures:
        for line in failures:
            say(f"!! {line}")
        return 4
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pull daily OMI NO2 for the two city boxes")
    parser.add_argument("--region-id", action="append", help="repeatable; default: both cities")
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--time-limit", type=float, default=0.0, help="seconds; 0 disables")
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--out", type=Path, default=PROCESSED)
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--refresh-granules", action="store_true")
    args = parser.parse_args(argv)

    token = token_from_environment()
    deadline = dt.timedelta(seconds=args.time_limit) if args.time_limit else None
    return run_regions(
        args.region_id,
        token=token,
        workers=args.workers,
        raw=args.raw,
        out=args.out,
        refresh_granules=args.refresh_granules,
        build=not args.no_build,
        deadline=deadline,
    )


if __name__ == "__main__":
    raise SystemExit(main())
