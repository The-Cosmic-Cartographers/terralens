"""One non-interactive command that pulls every Lineup series (NAS-60).

The routes are not interchangeable, so this module decides per variable instead
of per run:

* **Harmony** (GES DISC subsetting) for MERRA-2 aerosol and for GLDAS soil
  moisture and evapotranspiration. It returns one netCDF per month; the area mean
  is computed here and every parsed month is checkpointed, so a reset connection
  or a killed runner resumes instead of starting over.
* **T2M stays on Giovanni.** Harmony can subset M2TMNXSLV, but its output would
  land on the same `data/raw/t2m_<region>.csv` the published series came from, so
  the pull refuses that row instead of silently replacing a Giovanni source.
* **Giovanni** stays the route for IMERG, which Harmony does not serve: no
  coverage is registered for the collection, so a Harmony job is rejected before
  it starts. The pull refuses to invent a substitute and reports the series as
  blocked instead.
* **OMI NO2** has a CMR collection but no route verified from this machine; it is
  reported the same way rather than guessed at.

Credentials come from `EARTHDATA_TOKEN` only. The token is never printed, never
written to a checkpoint, and never reaches `provenance.json`.

Usage:
    EARTHDATA_TOKEN=... uv run python -m pipeline.pull --all
    uv run python -m pipeline.pull --variable-id aerosol --region-id ireland
    uv run python -m pipeline.pull --all --dry-run

Exit codes: 0 complete, 2 credentials/config, 3 time limit reached, 4 series failed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import requests
import xarray as xr
from requests.adapters import HTTPAdapter

from pipeline import build as build_module
from pipeline.regions import box_string, load_regions
from pipeline.registry import VARIABLES, Variable

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
CHECKPOINTS = Path("data/raw/.pull")
TOKEN_ENV = "EARTHDATA_TOKEN"
FILL = -9999.0
CHUNK_YEARS = 5
POLL_SECONDS = 5
POLL_TRIES = 40
EXIT_OK, EXIT_CONFIG, EXIT_TIME, EXIT_FAILED = 0, 2, 3, 4


@dataclass(frozen=True)
class Route:
    """Where one variable's months come from, and under what name."""

    collection: str
    field: str
    unit: str
    note: str = ""


# Verified against CMR on 2026-11-14; the collection ids are pinned rather than
# looked up at run time so a version bump upstream cannot silently change the
# product behind a series.
HARMONY_ROUTES: dict[str, Route] = {
    "t2m": Route("C1276812859-GES_DISC", "T2M", "K", "MERRA-2 M2TMNXSLV 5.12.4"),
    "aerosol": Route("C1276812866-GES_DISC", "TOTEXTTAU", "1", "MERRA-2 M2TMNXAER 5.12.4"),
    "soil_moisture_0_10": Route(
        "C1342986036-GES_DISC", "SoilMoi0_10cm_inst", "kg m-2", "GLDAS_NOAH025_M 2.1"
    ),
    "evapotranspiration": Route(
        "C1342986036-GES_DISC", "Evap_tavg", "kg m-2 s-1", "GLDAS_NOAH025_M 2.1"
    ),
}

# Rows whose committed series must not be replaced by a Harmony subset. T2M is
# here because a Harmony run would overwrite data/raw/t2m_<region>.csv, the file
# the published Giovanni series came from (NAS-60 review, Kevin).
GIOVANNI_ONLY: dict[str, str] = {
    "t2m": (
        "the committed T2M series is a Giovanni export; a Harmony subset must not "
        "overwrite data/raw/t2m_<region>.csv, so this row stays on Giovanni"
    ),
}

NO_ROUTE: dict[str, str] = {
    "precipitation": (
        "Harmony registers no coverage for GPM_3IMERGM (C2723754851-GES_DISC); "
        "Giovanni in 13-year windows is the working route, so export the CSV there"
    ),
    "no2": (
        "OMNO2d (C3333493715-GES_DISC) exists in CMR but no route through this "
        "pipeline has been verified yet; do not guess a variable name for it"
    ),
}


@dataclass
class Series:
    """One variable for one region: its months, its jobs, and where it is stored."""

    variable: Variable
    region_id: str
    box: tuple[float, float, float, float]
    months: dict[str, float] = field(default_factory=dict)
    jobs: list[str] = field(default_factory=list)
    extent: str | None = None

    @property
    def label(self) -> str:
        return f"{self.variable.variable_id}/{self.region_id}"

    def checkpoint(self) -> Path:
        return CHECKPOINTS / f"{self.variable.dataset_id}_{self.region_id}.json"

    def load(self) -> None:
        """Resume from the checkpoint, which stores months only — never a token."""
        path = self.checkpoint()
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.months = {
            str(month): float(value) for month, value in payload.get("months", {}).items()
        }
        self.jobs = list(payload.get("jobs", []))
        extent = payload.get("extent")
        self.extent = str(extent) if extent else None

    def save(self) -> None:
        CHECKPOINTS.mkdir(parents=True, exist_ok=True)
        self.checkpoint().write_text(
            json.dumps(
                {"months": self.months, "jobs": self.jobs, "extent": self.extent},
                indent=0,
            )
            + "\n",
            encoding="utf-8",
        )

    def wanted(self) -> list[str]:
        return [
            f"{year}-{month:02d}"
            for year in range(self.variable.start_year, self.variable.end_year + 1)
            for month in range(1, 13)
        ]

    def missing(self) -> list[str]:
        return [month for month in self.wanted() if month not in self.months]


def chunks(start_year: int, end_year: int, size: int = CHUNK_YEARS) -> Iterable[tuple[int, int]]:
    """Whole five-year windows, which is what Harmony answers reliably for these rows."""
    year = start_year
    while year <= end_year:
        last = min(year + size - 1, end_year)
        yield year, last
        year = last + 1


class TimeLimitReached(RuntimeError):
    """Raised when the run has spent its budget; the next run resumes."""


class MissingCredentials(RuntimeError):
    """Raised when no Earthdata token is available; the message says how to set one."""


class Deadline:
    """A monotonic budget checked between steps, so a slow slice cannot overrun it silently."""

    def __init__(self, seconds: float | None, clock: Callable[[], float] = time.monotonic) -> None:
        self.started = clock()
        self.seconds = seconds
        self._clock = clock

    def elapsed(self) -> float:
        return self._clock() - self.started

    def check(self) -> None:
        if self.seconds is not None and self.elapsed() > self.seconds:
            raise TimeLimitReached(f"time limit of {self.seconds:.0f}s reached")


_LOCAL = threading.local()


def session() -> requests.Session:
    """One keep-alive session per worker: the handshake, not the data, is the bottleneck."""
    current = getattr(_LOCAL, "session", None)
    if current is None:
        current = requests.Session()
        current.mount("https://", HTTPAdapter(pool_connections=8, pool_maxsize=8, max_retries=0))
        current.headers.update({"User-Agent": "terralens/0.1", "Connection": "keep-alive"})
        _LOCAL.session = current
    return current


@dataclass
class HarmonySource:
    """The only part that talks to NASA; swappable so the mechanics can be tested."""

    token: str
    attempts: int = 4

    def __post_init__(self) -> None:
        from harmony import Client

        self._client = Client(token=self.token)

    def submit(self, route: Route, box: tuple[float, ...], first: int, last: int) -> list[str]:
        """Submit one chunk and wait for its result URLs."""
        from harmony import BBox, Collection, Request

        west, south, east, north = box
        request = Request(
            collection=Collection(id=route.collection),
            spatial=BBox(west, south, east, north),
            temporal={"start": dt.datetime(first, 1, 1), "stop": dt.datetime(last, 12, 31)},
            variables=[route.field],
        )
        job = self._client.submit(request)
        status = "running"
        for _ in range(POLL_TRIES):
            time.sleep(POLL_SECONDS)
            status = self._client.status(job).get("status", "running")
            if status in ("successful", "failed", "canceled"):
                break
        if status != "successful":
            raise RuntimeError(f"job {job} ended {status}")
        return [job, *[str(url) for url in self._client.result_urls(job)]]

    def fetch(self, url: str) -> bytes | None:
        """Download one slice, retrying with a cap; a failed slice returns None."""
        headers: dict[str, str] = {}
        for attempt in range(self.attempts):
            if attempt >= self.attempts // 2:
                headers["Authorization"] = "Bearer " + self.token
            try:
                response = session().get(url, headers=headers, timeout=90, allow_redirects=True)
                if response.status_code == 200 and response.content[:4] == b"\x89HDF":
                    return response.content
            except requests.RequestException:
                pass
            time.sleep(min(0.4 + 0.4 * attempt, 2.5))
        return None


def centre_mask(
    lat: np.ndarray, lon: np.ndarray, box: tuple[float, float, float, float] | None
) -> np.ndarray | None:
    """Keep only cells whose centre falls inside the box (Giovanni's footprint rule).

    Harmony returns every cell that *intersects* the requested box, so an edge cell
    whose centre sits outside it is included. Averaging those pulls the mean towards
    the surrounding climate: on T2M Ireland that was 0.88 degC at worst. Giovanni
    analyses only centre-in-box cells, and this is what makes a Harmony series
    comparable with a Giovanni one (verified on T2M to 0.0005 degC).
    """
    if box is None:
        return None
    west, south, east, north = box
    return ((lat >= south) & (lat <= north))[:, None] & ((lon >= west) & (lon <= east))[None, :]


def slice_extent(
    payload: bytes, scratch: Path, *, box: tuple[float, float, float, float] | None = None
) -> str | None:
    """The W,S,E,N extent of the cells a slice actually averages, for provenance.

    A caller cannot infer this from the requested box: the mask drops edge cells, so
    the averaged footprint is usually one cell narrower on each side.
    """
    path = scratch / f"extent_{threading.get_ident()}_{time.time_ns()}.nc"
    path.write_bytes(payload)
    try:
        with xr.open_dataset(path, engine="netcdf4") as dataset:
            if "lat" not in dataset or "lon" not in dataset:
                return None
            lat = np.asarray(dataset["lat"].values)
            lon = np.asarray(dataset["lon"].values)
            inside = centre_mask(lat, lon, box)
            if inside is not None and inside.any():
                lat = lat[inside.any(axis=1)]
                lon = lon[inside.any(axis=0)]
            if not len(lat) or not len(lon):
                return None
            # same W,S,E,N order as requested_box, so the two can be read side by side
            return f"{lon.min():.2f},{lat.min():.2f},{lon.max():.2f},{lat.max():.2f}"
    finally:
        path.unlink(missing_ok=True)


def month_means(
    payload: bytes,
    field_name: str,
    scratch: Path,
    *,
    box: tuple[float, float, float, float] | None = None,
) -> dict[str, float]:
    """Cosine-latitude area mean of one monthly slice, centre-in-box only."""
    path = scratch / f"pull_{threading.get_ident()}_{time.time_ns()}.nc"
    path.write_bytes(payload)
    try:
        with xr.open_dataset(path, engine="netcdf4") as dataset:
            if field_name not in dataset:
                return {}
            month = str(dataset["time"].values[0])[:7]
            values = dataset[field_name].where(dataset[field_name] > FILL)
            lon_count = dataset.sizes["lon"]
            data = np.asarray(values.values).reshape(-1, lon_count)
            mask = np.isfinite(data)
            if box is not None and "lat" in dataset and "lon" in dataset:
                inside = centre_mask(
                    np.asarray(dataset["lat"].values), np.asarray(dataset["lon"].values), box
                )
                if inside is not None:
                    mask = mask & inside
            if not mask.any():
                return {}
            if "lat" in values.dims:
                weights = np.cos(np.deg2rad(np.asarray(dataset["lat"].values)))[:, None]
                weight_sum = float(np.sum(np.where(mask, weights, 0.0)))
                if weight_sum == 0:
                    return {}
                mean = float(np.sum(np.where(mask, data * weights, 0.0)) / weight_sum)
            else:
                mean = float(data[mask][0])
            return {month: mean}
    finally:
        path.unlink(missing_ok=True)


def write_csv(series: Series, route: Route) -> Path:
    """Write the pipeline's raw CSV shape, which `pipeline.build` already parses."""
    rows = [f"{month},{series.months[month]:.6g}" for month in sorted(series.months)]
    west, south, east, north = series.box
    out = RAW / f"{series.variable.variable_id}_{series.region_id}.csv"
    header = [
        f"# NASA Harmony subset of {route.collection} ({route.field}), area mean",
        f"# region {series.region_id} box {west},{south},{east},{north} | {len(rows)} months",
        f"Parameter,{route.field}",
        f"Unit,{route.unit}",
        "Month,Mean",
    ]
    out.write_text("\n".join(header + rows) + "\n", encoding="utf-8")
    (RAW / f"{series.variable.variable_id}_{series.region_id}.meta.json").write_text(
        json.dumps(
            {
                "variable": series.variable.variable_id,
                "region": series.region_id,
                "collection": route.collection,
                "field": route.field,
                "native_unit": route.unit,
                "months": len(rows),
                "first": rows[0].split(",")[0],
                "last": rows[-1].split(",")[0],
                "jobs": sorted(set(series.jobs)),
                "analyzable_region": series.extent,
                "access_route": "NASA Harmony (GES DISC subset)",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return out


def build_series(series: Series, route: Route, csv_path: Path, out_root: Path) -> Path:
    """Hand the CSV to the builder so `data/processed/` is ready after the pull."""
    spec = series.variable
    parquet, _ = build_module.build(
        csv_path,
        dataset_id=spec.dataset_id,
        variable_id=spec.variable_id,
        region_id=series.region_id,
        product=spec.product,
        version=spec.version,
        native_unit=route.unit,
        output_unit=spec.output_unit,
        spatial_resolution=spec.spatial_resolution,
        giovanni_variable_id=route.field,
        requested_box=box_string(
            {
                "west": series.box[0],
                "south": series.box[1],
                "east": series.box[2],
                "north": series.box[3],
            }
        ),
        analyzable_region=series.extent,
        permalink=f"https://harmony.earthdata.nasa.gov/jobs/{series.jobs[-1]}"
        if series.jobs
        else None,
        access_date=dt.date.today().isoformat(),
        start_year=None,
        end_year=None,
        out_root=out_root,
        access_route="NASA Harmony (GES DISC subset)",
    )
    return parquet


def pull_series(
    series: Series,
    route: Route,
    source: HarmonySource,
    *,
    deadline: Deadline,
    workers: int,
    rounds: int,
    scratch: Path,
    say: Callable[[str], None] = print,
) -> None:
    """Fill one series from Harmony, chunk by chunk, checkpointing every chunk."""
    series.load()
    if not series.missing():
        say(f"  {series.label}: complete from checkpoint ({len(series.months)} months)")
        return

    for round_number in range(rounds + 1):
        for first, last in chunks(series.variable.start_year, series.variable.end_year):
            deadline.check()
            wanted = [f"{y}-{m:02d}" for y in range(first, last + 1) for m in range(1, 13)]
            if all(month in series.months for month in wanted):
                continue
            outcomes = source.submit(route, series.box, first, last)
            job, urls = outcomes[0], outcomes[1:]
            series.jobs.append(job)
            say(f"  {series.label} {first}-{last}: {len(urls)} slices")
            payloads: list[bytes] = []
            pending = list(urls)
            for attempt in range(2):
                if not pending:
                    break
                with ThreadPoolExecutor(max_workers=max(1, workers - attempt)) as pool:
                    results = list(pool.map(source.fetch, pending))
                payloads.extend(item for item in results if item is not None)
                pending = [url for url, item in zip(pending, results, strict=True) if item is None]
                if pending:
                    say(f"    pass {attempt + 1}: {len(pending)} slices still missing")
                    time.sleep(1.5 * (attempt + 1))
            if series.extent is None and payloads:
                series.extent = slice_extent(payloads[0], scratch, box=series.box)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                parsed = list(
                    pool.map(
                        lambda item: month_means(item, route.field, scratch, box=series.box),
                        payloads,
                    )
                )
            for result in parsed:
                for month, mean in result.items():
                    series.months.setdefault(month, mean)
            series.save()
            say(f"    months now {len(series.months)}/{len(series.wanted())}")
        if not series.missing():
            break
        say(f"  {series.label}: {len(series.missing())} months missing, round {round_number + 2}")


# NO2 is a two-city row (doc 11), not a fifth Lineup column: its boxes are the
# Dublin and Delhi city points, and no other variable is defined over them.
NO2_REGIONS = ("dublin_no2", "delhi_no2")


def _applies(variable_id: str, region_id: str) -> bool:
    """Whether this variable is defined for this region at all."""
    return (variable_id == "no2") == (region_id in NO2_REGIONS)


def plan(
    variable_ids: list[str] | None, region_ids: list[str] | None
) -> tuple[list[tuple[Variable, str, Route]], list[tuple[str, str, str]]]:
    """Return (work, blocked) for the requested slices."""
    regions = load_regions()
    wanted_regions = region_ids or sorted(regions)
    selected = variable_ids or list(VARIABLES)
    work: list[tuple[Variable, str, Route]] = []
    blocked: list[tuple[str, str, str]] = []
    for variable_id in selected:
        spec = VARIABLES[variable_id]
        for region_id in wanted_regions:
            if region_id not in regions:
                raise KeyError(
                    f"unknown region_id {region_id!r}; known: {', '.join(sorted(regions))}"
                )
            if not _applies(variable_id, region_id):
                continue
            if variable_id in GIOVANNI_ONLY:
                blocked.append((variable_id, region_id, GIOVANNI_ONLY[variable_id]))
                continue
            route = HARMONY_ROUTES.get(variable_id)
            if route is None:
                blocked.append((variable_id, region_id, NO_ROUTE.get(variable_id, "no route")))
            else:
                work.append((spec, region_id, route))
    return work, blocked


def token_from_environment(env: dict[str, str] | None = None) -> str:
    """Read the Earthdata token, failing with instructions rather than a blank request."""
    value = (env or os.environ).get(TOKEN_ENV, "").strip()
    if not value:
        raise MissingCredentials(
            f"{TOKEN_ENV} is not set. Export an Earthdata bearer token before running "
            f"(on CI it belongs in a repository secret of that name); the token is never "
            f"read from a file or printed."
        )
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pull every Lineup series, then build them")
    parser.add_argument("--all", action="store_true", help="every variable and region")
    parser.add_argument("--variable-id", action="append", help="repeatable; default: all")
    parser.add_argument("--region-id", action="append", help="repeatable; default: all")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--attempts", type=int, default=4, help="download attempts per slice")
    parser.add_argument("--rounds", type=int, default=2, help="extra passes over missing months")
    parser.add_argument("--time-limit", type=float, default=1800.0, help="seconds; 0 disables")
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--out", type=Path, default=PROCESSED)
    parser.add_argument("--no-build", action="store_true", help="pull only, skip data/processed")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and exit")
    args = parser.parse_args(argv)

    if not args.all and not args.variable_id:
        parser.error("choose --all or at least one --variable-id")
    variable_ids = args.variable_id or list(VARIABLES)

    try:
        work, blocked = plan(variable_ids, args.region_id)
    except KeyError as error:
        parser.error(str(error))

    if args.dry_run:
        for spec, region_id, route in work:
            print(f"{spec.variable_id}/{region_id} <- Harmony {route.collection} ({route.field})")
        for variable_id, region_id, reason in blocked:
            print(f"{variable_id}/{region_id} <- BLOCKED: {reason}")
        return EXIT_OK

    try:
        token = token_from_environment()
    except MissingCredentials as error:
        print(error)
        return EXIT_CONFIG
    source = HarmonySource(token=token, attempts=args.attempts)
    deadline = Deadline(args.time_limit or None)
    scratch = Path(os.environ.get("TEMP", "/tmp"))
    args.raw.mkdir(parents=True, exist_ok=True)
    regions = load_regions()

    failures: list[str] = []
    for spec, region_id, route in work:
        region = regions[region_id]
        series = Series(
            variable=spec,
            region_id=region_id,
            box=(
                float(region["west"]),
                float(region["south"]),
                float(region["east"]),
                float(region["north"]),
            ),
        )
        print(f"== {series.label}")
        try:
            pull_series(
                series,
                route,
                source,
                deadline=deadline,
                workers=args.workers,
                rounds=args.rounds,
                scratch=scratch,
            )
            if series.missing():
                failures.append(f"{series.label}: {len(series.missing())} months missing")
                continue
            csv_path = write_csv(series, route)
            if not args.no_build:
                build_series(series, route, csv_path, args.out)
            print(f"  {series.label}: {len(series.months)} months -> {csv_path}")
        except TimeLimitReached as stop:
            print(f"!! {stop}; rerun the same command to resume from checkpoints")
            return EXIT_TIME
        except Exception as error:  # noqa: BLE001 - one bad series must not end the run
            failures.append(f"{series.label}: {error!r}")
            print(f"!! {series.label}: {error!r}")

    for variable_id, region_id, reason in blocked:
        print(f"-- {variable_id}/{region_id}: blocked - {reason}")

    print(f"\n{len(work) - len(failures)}/{len(work)} series built in {deadline.elapsed():.0f}s")
    if failures:
        print("failed:")
        for line in failures:
            print(f"  - {line}")
        return EXIT_FAILED
    if blocked:
        print(f"{len(blocked)} series blocked by route, not by failure")
        return EXIT_FAILED
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
