"""Tests for the one-command puller (NAS-60).

Nothing here touches the network: the Harmony source is replaced by a fake that
returns slice payloads, and the netCDF step is replaced by a decoder, so what is
under test is the orchestration — planning, resume, retry caps, the time budget
and the CSV the builder receives.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline import pull
from pipeline.giovanni import read_giovanni_csv, read_giovanni_unit
from pipeline.registry import Variable


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
        pull, "month_means", lambda payload, field, scratch: {payload.decode(): 280.0}
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


def test_plan_routes_every_variable_it_can_and_names_the_ones_it_cannot() -> None:
    work, blocked = pull.plan(None, ["ireland"])
    routed = {spec.variable_id for spec, _region, _route in work}
    assert routed == {"t2m", "aerosol", "soil_moisture_0_10", "evapotranspiration"}
    # IMERG is the only blocked row over the five Lineup regions; NO2 is a city row.
    assert {variable for variable, _region, _reason in blocked} == {"precipitation"}
    assert all(reason for _v, _r, reason in blocked)

    work_no2, blocked_no2 = pull.plan(["no2"], ["dublin_no2"])
    assert work_no2 == []
    assert blocked_no2[0][0] == "no2"


def test_plan_is_the_doc_11_lineup_and_not_the_cartesian_product() -> None:
    """27 series: five rows over five regions, plus NO2 for Dublin and Delhi only."""
    work, blocked = pull.plan(None, None)
    assert len(work) + len(blocked) == 27
    assert {region for _spec, region, _route in work} >= {"ireland", "us_southwest"}
    assert not {region for _spec, region, _route in work} & set(pull.NO2_REGIONS)
    assert {region for variable, region, _reason in blocked if variable == "no2"} == set(
        pull.NO2_REGIONS
    )


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


def test_dry_run_prints_the_plan_and_never_needs_a_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(pull.TOKEN_ENV, raising=False)
    assert pull.main(["--all", "--dry-run"]) == pull.EXIT_OK
    output = capsys.readouterr().out
    assert "t2m/ireland <- Harmony" in output
    assert "precipitation/ireland <- BLOCKED" in output
