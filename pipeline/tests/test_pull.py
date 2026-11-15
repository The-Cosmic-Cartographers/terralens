"""Tests for the one-command puller (NAS-60).

Nothing here touches the network: the Harmony source is replaced by a fake that
returns slice payloads, and the netCDF step is replaced by a decoder, so what is
under test is the orchestration — planning, resume, retry caps, the time budget
and the CSV the builder receives.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest

from pipeline import pull
from pipeline.giovanni import read_giovanni_csv, read_giovanni_unit
from pipeline.registry import Variable

# The autouse fixture below replaces these with fakes; these are the real ones, for the
# tests that exercise the netCDF math itself.
_REAL_MONTH_MEANS = pull.month_means
_REAL_SLICE_EXTENT = pull.slice_extent


def _variable(start: int = 2001, end: int = 2002) -> Variable:
    return Variable(
        variable_id="t2m",
        dataset_id="test_dataset",
        product="test product (TEST)",
        version="1.0",
        native_unit="K",
        output_unit="°C",
        spatial_resolution="0.5°",
        giovanni_variable_id="T2M",
        start_year=start,
        end_year=end,
    )


class FakeSource:
    """Stands in for Harmony: records submissions, hands back one payload per month."""

    def __init__(self, *, fail_every: int = 0, dead: bool = False) -> None:
        self.submitted: list[tuple[int, int]] = []
        self.fail_every = fail_every
        self.dead = dead
        self.calls = 0

    def submit(self, route: pull.Route, box: tuple[float, ...], first: int, last: int) -> list[str]:
        self.submitted.append((first, last))
        urls = [f"{year}-{month:02d}" for year in range(first, last + 1) for month in range(1, 13)]
        return ["job-123", *urls]

    def fetch(self, url: str) -> bytes | None:
        self.calls += 1
        if self.dead:
            return None
        if self.fail_every and self.calls % self.fail_every == 0:
            return None
        return url.encode()


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep checkpoints and raw files inside the test's temp directory."""
    raw = tmp_path / "raw"
    raw.mkdir()
    checkpoints = raw / ".pull"
    monkeypatch.setattr(pull, "RAW", raw)
    monkeypatch.setattr(pull, "CHECKPOINTS", checkpoints)
    monkeypatch.setattr(
        pull,
        "month_means",
        lambda payload, field, scratch, box=None: {payload.decode(): 280.0},
    )
    monkeypatch.setattr(
        pull, "slice_extent", lambda payload, scratch, box=None: "51.40,55.40,-10.50,-6.00"
    )
    monkeypatch.setattr(pull.time, "sleep", lambda _seconds: None)


def _series(variable: Variable | None = None) -> pull.Series:
    return pull.Series(
        variable=variable or _variable(),
        region_id="ireland",
        box=(-10.5, 51.4, -6.0, 55.4),
    )


def test_chunks_cover_the_window_in_whole_five_year_steps() -> None:
    assert list(pull.chunks(2001, 2002)) == [(2001, 2002)]
    assert list(pull.chunks(2000, 2011)) == [(2000, 2004), (2005, 2009), (2010, 2011)]


def test_plan_routes_all_five_mvp_variables_without_blocking_rows() -> None:
    work, cities, blocked = pull.plan(None, ["ireland"])
    routed = {spec.variable_id for spec, _region, _route in work}
    assert routed == {
        "t2m",
        "aerosol",
        "soil_moisture_0_5",
        "evapotranspiration",
        "precipitation",
    }
    assert cities == []
    assert blocked == []


def _slice(tmp_path: Path, lat: list[float], lon: list[float], values: list[list[float]]) -> bytes:
    """One monthly netCDF slice, the shape Harmony returns."""
    import numpy as np
    import xarray as xr

    dataset = xr.Dataset(
        {"T2M": (("time", "lat", "lon"), np.array([values], dtype="float32"))},
        coords={"time": [np.datetime64("2001-01-01")], "lat": lat, "lon": lon},
    )
    path = tmp_path / "slice.nc"
    dataset.to_netcdf(path, engine="netcdf4")
    payload = path.read_bytes()
    path.unlink()
    return payload


def test_centre_mask_drops_edge_cells_whose_centre_is_outside_the_box() -> None:
    import numpy as np

    lat = np.array([51.5, 52.5, 55.5])
    lon = np.array([-10.0, -8.0])
    inside = pull.centre_mask(lat, lon, (-10.5, 51.4, -6.0, 55.4))
    assert inside is not None
    assert inside[:, 0].tolist() == [True, True, False]
    assert pull.centre_mask(lat, lon, None) is None


def test_month_means_averages_only_cells_inside_the_box(tmp_path: Path) -> None:
    import math

    payload = _slice(
        tmp_path, [51.5, 52.5, 55.5], [-10.0, -8.0], [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
    )
    box = (-10.5, 51.4, -6.0, 55.4)

    narrow = _REAL_MONTH_MEANS(payload, "T2M", tmp_path, box=box)["2001-01"]
    w1, w2 = math.cos(math.radians(51.5)), math.cos(math.radians(52.5))
    assert narrow == pytest.approx((w1 * (1 + 2) + w2 * (3 + 4)) / (2 * w1 + 2 * w2))

    wide = _REAL_MONTH_MEANS(payload, "T2M", tmp_path)["2001-01"]
    assert wide > narrow  # the outside cell is warmer, so leaving it in lifts the mean


def test_slice_extent_reports_the_cells_that_were_actually_averaged(tmp_path: Path) -> None:
    payload = _slice(
        tmp_path, [51.5, 52.5, 55.5], [-10.0, -8.0], [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
    )
    assert _REAL_SLICE_EXTENT(payload, tmp_path, box=(-10.5, 51.4, -6.0, 55.4)) == (
        "-10.00,51.50,-8.00,52.50"
    )


def test_the_checkpoint_keeps_the_footprint_across_runs() -> None:
    first = _series()
    first.months = {"2001-01": 280.0}
    first.extent = "51.40,55.40,-10.50,-6.00"
    first.save()

    resumed = _series()
    resumed.load()
    assert resumed.extent == "51.40,55.40,-10.50,-6.00"


def test_precipitation_is_a_harmony_route_to_merra2_prectotcorr() -> None:
    """The long record uses MERRA-2 bias-corrected precipitation through Harmony."""
    work, cities, blocked = pull.plan(["precipitation"], ["ireland"])
    assert not blocked
    route = work[0][2]
    assert route is pull.HARMONY_ROUTES["precipitation"]
    assert route.collection == "C1276812868-GES_DISC"
    assert route.field == "PRECTOTCORR"
    assert route.unit == "kg m-2 s-1"
    assert route.access_route == pull.HARMONY_ACCESS


def test_regional_mean_weights_cells_by_the_cosine_of_latitude() -> None:
    field = pd.DataFrame({"lat": [0.5, 60.5], "lon": [0.5, 0.5], "value": [10.0, 20.0]})
    mean = pull.regional_mean(field, (0.0, 0.0, 1.0, 61.0))
    low = math.cos(math.radians(0.5))
    high = math.cos(math.radians(60.5))
    assert mean == pytest.approx((10.0 * low + 20.0 * high) / (low + high))
    # a plain mean would be 15.0; the tropical cell must count for more
    assert mean < 14.0


def test_regional_mean_refuses_a_month_that_is_mostly_empty() -> None:
    field = pd.DataFrame({"lat": [0.5, 60.5], "lon": [0.5, 0.5], "value": [float("nan"), 20.0]})
    assert pull.regional_mean(field, (0.0, 0.0, 1.0, 61.0)) is None


def test_the_csv_records_which_route_produced_it() -> None:
    series = _series()
    series.months = {"2001-01": 50.0}
    path = pull.write_csv(series, pull.IMERG_ROUTE)
    meta = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8"))
    assert meta["access_route"].startswith("NASA GES DISC direct")


def test_t2m_uses_harmony_and_preserves_the_giovanni_raw_export() -> None:
    work, cities, blocked = pull.plan(["t2m"], ["ireland"])
    assert len(work) == 1
    assert work[0][2] is pull.HARMONY_ROUTES["t2m"]
    assert cities == []
    assert blocked == []

    old_export = pull.RAW / "t2m_ireland.csv"
    old_export.write_text("Giovanni source", encoding="utf-8")
    series = _series()
    series.months = {"2001-01": 280.0}
    new_export = pull.write_csv(series, pull.HARMONY_ROUTES["t2m"])
    assert new_export.name == "t2m_ireland_harmony.csv"
    assert old_export.read_text(encoding="utf-8") == "Giovanni source"

    work_no2, cities_no2, blocked_no2 = pull.plan(["no2"], ["dublin_no2"])
    assert work_no2 == []
    assert blocked_no2 == []
    assert cities_no2 == ["dublin_no2"]


def test_plan_is_the_doc_11_lineup_and_not_the_cartesian_product() -> None:
    """27 series: five rows over five regions, plus NO2 for Dublin and Delhi only."""
    work, cities, blocked = pull.plan(None, None)
    assert len(work) + len(cities) + len(blocked) == 27
    assert len(work) == 25
    assert blocked == []
    assert {region for _spec, region, _route in work} >= {"ireland", "us_southwest"}
    assert not {region for _spec, region, _route in work} & set(pull.NO2_REGIONS)
    assert set(cities) == set(pull.NO2_REGIONS)
    assert not {region for variable, region, _reason in blocked if variable == "no2"}


def test_plan_rejects_an_unknown_region() -> None:
    with pytest.raises(KeyError):
        pull.plan(["t2m"], ["atlantis"])


def test_missing_token_says_what_to_set_and_never_leaks_a_value() -> None:
    with pytest.raises(pull.MissingCredentials) as caught:
        pull.token_from_environment({})
    assert pull.TOKEN_ENV in str(caught.value)
    assert pull.token_from_environment({pull.TOKEN_ENV: "abc"}) == "abc"


def test_main_exits_with_config_code_when_the_token_is_absent(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(pull.TOKEN_ENV, raising=False)
    assert pull.main(["--variable-id", "t2m", "--region-id", "ireland"]) == pull.EXIT_CONFIG
    assert pull.TOKEN_ENV in capsys.readouterr().out


def test_deadline_stops_a_run_that_overspends() -> None:
    ticks = iter([0.0, 10.0, 40.0])
    deadline = pull.Deadline(30.0, clock=lambda: next(ticks))
    deadline.check()
    with pytest.raises(pull.TimeLimitReached):
        deadline.check()


def test_series_round_trips_through_its_checkpoint() -> None:
    series = _series()
    series.months = {"2001-01": 280.5}
    series.jobs = ["job-1"]
    series.save()

    resumed = _series()
    resumed.load()
    assert resumed.months == {"2001-01": 280.5}
    assert resumed.jobs == ["job-1"]
    assert json.loads(series.checkpoint().read_text(encoding="utf-8"))["months"]


def test_pull_fills_every_month_and_writes_a_buildable_csv() -> None:
    series = _series()
    source = FakeSource()
    pull.pull_series(
        series,
        pull.HARMONY_ROUTES["t2m"],
        source,
        deadline=pull.Deadline(None),
        workers=2,
        rounds=0,
        scratch=Path("."),
    )

    assert not series.missing()
    assert source.submitted == [(2001, 2002)]

    csv_path = pull.write_csv(series, pull.HARMONY_ROUTES["t2m"])
    assert read_giovanni_unit(csv_path) == "K"
    parsed = read_giovanni_csv(csv_path)
    assert len(parsed) == 24
    assert parsed["value"].iloc[0] == pytest.approx(280.0)


def test_a_second_run_resumes_instead_of_resubmitting() -> None:
    first = _series()
    source = FakeSource()
    pull.pull_series(
        first,
        pull.HARMONY_ROUTES["t2m"],
        source,
        deadline=pull.Deadline(None),
        workers=2,
        rounds=0,
        scratch=Path("."),
    )

    resumed = _series()
    second_source = FakeSource()
    pull.pull_series(
        resumed,
        pull.HARMONY_ROUTES["t2m"],
        second_source,
        deadline=pull.Deadline(None),
        workers=2,
        rounds=0,
        scratch=Path("."),
    )

    assert second_source.submitted == []
    assert len(resumed.months) == 24


def test_failed_slices_are_retried_then_reported_not_swallowed() -> None:
    series = _series()
    source = FakeSource(fail_every=3)

    pull.pull_series(
        series,
        pull.HARMONY_ROUTES["t2m"],
        source,
        deadline=pull.Deadline(None),
        workers=2,
        rounds=0,
        scratch=Path("."),
    )

    assert len(series.months) >= 20
    assert source.calls >= 24


def test_a_dead_source_stops_after_the_round_cap() -> None:
    series = _series()
    source = FakeSource(dead=True)

    pull.pull_series(
        series,
        pull.HARMONY_ROUTES["t2m"],
        source,
        deadline=pull.Deadline(None),
        workers=2,
        rounds=1,
        scratch=Path("."),
    )

    assert source.submitted == [(2001, 2002), (2001, 2002)]
    assert series.missing()


def test_build_is_handed_the_registry_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_build(csv_path: Path, **kwargs: object) -> tuple[Path, Path]:
        captured.update(kwargs)
        captured["csv"] = csv_path
        return Path("out.parquet"), Path("provenance.json")

    monkeypatch.setattr(pull.build_module, "build", fake_build)
    series = _series()
    series.months = {"2001-01": 280.0}
    series.jobs = ["job-9"]
    csv_path = pull.write_csv(series, pull.HARMONY_ROUTES["t2m"])

    pull.build_series(series, pull.HARMONY_ROUTES["t2m"], csv_path, Path("processed"))

    assert captured["dataset_id"] == "test_dataset"
    assert captured["variable_id"] == "t2m"
    assert captured["native_unit"] == "K"
    assert captured["access_route"] == "NASA Harmony (GES DISC subset)"
    assert "job-9" in str(captured["permalink"])


def test_build_is_handed_the_footprint_as_analyzable_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_build(csv_path: Path, **kwargs: object) -> tuple[Path, Path]:
        captured.update(kwargs)
        return Path("out.parquet"), Path("provenance.json")

    monkeypatch.setattr(pull.build_module, "build", fake_build)
    series = _series()
    series.months = {"2001-01": 280.0}
    series.extent = "-10.50,51.50,-6.50,55.00"
    csv_path = pull.write_csv(series, pull.HARMONY_ROUTES["t2m"])

    pull.build_series(series, pull.HARMONY_ROUTES["t2m"], csv_path, Path("processed"))

    assert captured["analyzable_region"] == "-10.50,51.50,-6.50,55.00"


def test_a_stale_s_n_w_e_extent_is_rebuilt_before_the_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The old checkpoint wrote S,N,W,E; the build must not pass that through."""
    captured: dict[str, object] = {}

    def fake_build(csv_path: Path, **kwargs: object) -> tuple[Path, Path]:
        captured.update(kwargs)
        return Path("out.parquet"), Path("provenance.json")

    monkeypatch.setattr(pull.build_module, "build", fake_build)
    series = _series()
    series.months = {"2001-01": 280.0}
    series.extent = "51.50,55.00,-10.50,-6.50"
    csv_path = pull.write_csv(series, pull.HARMONY_ROUTES["t2m"])

    pull.build_series(series, pull.HARMONY_ROUTES["t2m"], csv_path, Path("processed"))

    passed = str(captured["analyzable_region"])
    assert pull.parse_extent(passed) is not None
    assert passed == pull.grid_extent(series.box)


def test_dry_run_prints_the_plan_and_never_needs_a_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(pull.TOKEN_ENV, raising=False)
    assert pull.main(["--all", "--dry-run"]) == pull.EXIT_OK
    output = capsys.readouterr().out
    assert "aerosol/ireland <- Harmony" in output
    assert "no2/dublin_no2 <- OPeNDAP" in output
    assert "precipitation/ireland <- Harmony" in output
    assert "t2m/ireland <- Harmony" in output
    assert "t2m/ireland <- BLOCKED" not in output


def test_token_can_be_read_from_env_file_and_environment_overrides_it(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('EARTH_DATA_API="from-file"\n', encoding="utf-8")

    assert pull.token_from_environment(env={}, env_file=env_file) == "from-file"
    assert (
        pull.token_from_environment(
            env={pull.TOKEN_ENV: "from-environment"}, env_file=env_file
        )
        == "from-environment"
    )


def test_grid_extent_reproduces_the_centre_in_box_footprint() -> None:
    """The deterministic fallback must agree with what a payload would have measured."""
    gldas = {"step": (0.25, 0.25), "first_centre": (-89.875, -179.875)}
    assert pull.grid_extent((-10.0, 36.0, 3.5, 44.0), **gldas) == "-9.88,36.12,3.38,43.88"
    assert pull.grid_extent((68.0, 22.0, 78.0, 32.0), **gldas) == "68.12,22.12,77.88,31.88"
    # MERRA-2: latitudes on whole and half degrees, longitudes on multiples of 0.625
    assert pull.grid_extent((-10.5, 51.4, -6.0, 55.4)) == "-10.00,51.50,-6.25,55.00"


def test_an_extent_in_the_wrong_order_is_refused() -> None:
    """S,N,W,E from the old bug is not a W,S,E,N footprint and must not pass."""
    assert pull.parse_extent("-6.38,53.38,-6.12,53.38") is not None
    assert pull.parse_extent("53.38,53.38,-6.38,-6.12") is None
    assert pull.parse_extent("") is None
    assert pull.parse_extent("1,2,3") is None


def test_harmony_t2m_is_available_for_every_region() -> None:
    work, cities, blocked = pull.plan(["t2m"], None)
    climate_regions = set(pull.load_regions()) - set(pull.NO2_REGIONS)
    assert len(work) == len(climate_regions)
    assert {region_id for _spec, region_id, _route in work} == climate_regions
    assert all(route is pull.HARMONY_ROUTES["t2m"] for _spec, _region, route in work)
    assert cities == []
    assert blocked == []
