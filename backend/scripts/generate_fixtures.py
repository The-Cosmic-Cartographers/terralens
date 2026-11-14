"""Generate the SAMPLE fixtures in data/fixtures.

Everything here is made up. Series are synthetic (a known trend, a seasonal cycle
and noise) and the statistics are computed on them with a simple method
(Kendall's tau and Theil-Sen on annual means) so the numbers hang together in
the UI. None of it is NASA data, and none of it is a finding.

The output mirrors the layout of the real data/ folder, so the backend can point
at data/fixtures with one setting (TERRALENS_DATA_DIR):

    PYTHONPATH=backend uv run python -m scripts.generate_fixtures

The generator is deterministic: running it twice gives the same files.
"""

import datetime as dt
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy import stats

from app.models import (
    CatalogueItem,
    ChangePoint,
    Lineup,
    LineupRow,
    Metadata,
    Provenance,
    Region,
    RegionProvenance,
    SeasonalSlopes,
    SeriesRow,
    TrendResult,
    Window,
    Windows,
)

SAMPLE = "SAMPLE — NOT NASA DATA"
MIN_WINDOW_YEARS = 10
SIGNIFICANT = 0.05
WEAK = 0.10


@dataclass(frozen=True)
class RegionSpec:
    region_id: str
    name: str
    box: tuple[float, float, float, float]  # W, S, E, N
    total_cells: int


@dataclass(frozen=True)
class DatasetSpec:
    dataset_id: str
    variable_id: str
    label: str
    definition: str
    unit: str
    unit_per_year: str
    product_type: str
    start: int
    end: int
    # region_id -> (base, seasonal amplitude, monthly noise s.d., slope per year)
    params: dict[str, tuple[float, float, float, float]]
    withheld_regions: tuple[str, ...] = ()


REGIONS = [
    RegionSpec("ireland", "Ireland", (-10.5, 51.4, -6.0, 55.4), 56),
    RegionSpec("iberia", "Iberia", (-10.0, 36.0, 0.0, 44.0), 256),
]

DATASETS = [
    DatasetSpec(
        "sample_t2m",
        "t2m",
        "Air temperature (2 m)",
        "How warm the air is at about head height",
        "°C",
        "°C/yr",
        "reanalysis",
        1981,
        2025,
        {"ireland": (10.0, 5.0, 0.7, 0.035), "iberia": (15.0, 8.0, 0.9, 0.06)},
    ),
    DatasetSpec(
        "sample_soil_moisture_0_10cm",
        "soil_moisture_0_10cm",
        "Soil moisture (0–10 cm)",
        "How wet the top layer of soil is",
        "kg/m²",
        "kg/m²/yr",
        "land_model",
        2000,
        2025,
        {"ireland": (22.0, 3.0, 1.8, 0.02), "iberia": (14.0, 4.0, 1.8, -0.10)},
    ),
    DatasetSpec(
        "sample_evapotranspiration",
        "evapotranspiration",
        "Evapotranspiration",
        "Water returned to the air by soil and plants",
        "mm/day",
        "mm/day/yr",
        "land_model",
        2000,
        2025,
        {"ireland": (1.6, 1.0, 0.18, 0.0), "iberia": (1.9, 1.2, 0.18, 0.0045)},
    ),
    DatasetSpec(
        "sample_precipitation",
        "precipitation",
        "Precipitation",
        "Rain and snow reaching the ground",
        "mm/month",
        "mm/month/yr",
        "satellite",
        2001,
        2024,
        {"ireland": (90.0, 25.0, 22.0, 0.7), "iberia": (45.0, 20.0, 16.0, -1.1)},
    ),
    DatasetSpec(
        "sample_aerosol",
        "aerosol_optical_depth",
        "Aerosol optical depth",
        "How hazy the air is from dust, smoke and pollution",
        "unitless",
        "1/yr",
        "reanalysis",
        2003,
        2025,
        {"ireland": (0.15, 0.03, 0.03, 0.00058), "iberia": (0.20, 0.04, 0.03, -0.002)},
        withheld_regions=("iberia",),
    ),
]

SERIES_SCHEMA = pa.schema(
    [
        ("dataset_id", pa.string()),
        ("variable_id", pa.string()),
        ("region_id", pa.string()),
        ("timestamp", pa.date32()),
        ("value", pa.float64()),
        ("unit", pa.string()),
        ("anomaly", pa.float64()),
        ("valid_cell_count", pa.int64()),
        ("total_cell_count", pa.int64()),
        ("coverage_fraction", pa.float64()),
        ("n_valid_days", pa.int64()),
        ("quality_summary", pa.string()),
        ("source", pa.string()),
    ]
)


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, p_values[i] * m / rank)
        adjusted[i] = running
    return adjusted


def verdict_for(adjusted_p: float) -> str:
    if adjusted_p < SIGNIFICANT:
        return "significant"
    if adjusted_p < WEAK:
        return "weak_evidence"
    return "no_clear_trend"


def make_series(spec: DatasetSpec, region: RegionSpec, rng: np.random.Generator) -> list[SeriesRow]:
    base, amplitude, noise, slope = spec.params[region.region_id]
    withheld = region.region_id in spec.withheld_regions
    phi = 0.3
    eps = 0.0
    raw: list[tuple[dt.date, float | None, int]] = []
    for year in range(spec.start, spec.end + 1):
        for month in range(1, 13):
            t = (year - spec.start) + (month - 1) / 12
            eps = phi * eps + rng.normal(0.0, noise * math.sqrt(1 - phi**2))
            value = (
                base + slope * t + amplitude * math.sin(2 * math.pi * (month - 1) / 12 - 1.2) + eps
            )
            if withheld and rng.random() < 0.35:
                valid = int(region.total_cells * rng.uniform(0.3, 0.45))
                raw.append((dt.date(year, month, 1), None, valid))
            else:
                valid = region.total_cells - int(rng.integers(0, max(1, region.total_cells // 20)))
                raw.append((dt.date(year, month, 1), round(value, 4), valid))

    climatology: dict[int, float] = {}
    for month in range(1, 13):
        values = [v for d, v, _ in raw if d.month == month and v is not None]
        climatology[month] = sum(values) / len(values)

    rows = []
    for stamp, value, valid in raw:
        rows.append(
            SeriesRow(
                dataset_id=spec.dataset_id,
                variable_id=spec.variable_id,
                region_id=region.region_id,
                timestamp=stamp,
                value=value,
                unit=spec.unit,
                anomaly=None if value is None else round(value - climatology[stamp.month], 4),
                valid_cell_count=valid,
                total_cell_count=region.total_cells,
                coverage_fraction=round(valid / region.total_cells, 4),
                quality_summary="synthetic",
                source=SAMPLE,
            )
        )
    return rows


def annual_means(rows: list[SeriesRow], field: str) -> dict[int, float]:
    by_year: dict[int, list[float]] = {}
    for row in rows:
        number = getattr(row, field)
        if number is not None:
            by_year.setdefault(row.timestamp.year, []).append(number)
    return {year: sum(v) / len(v) for year, v in by_year.items() if len(v) >= 6}


def trend_stats(years: list[int], values: list[float]) -> tuple[float, tuple[float, float], float]:
    slope, _, low, high = stats.theilslopes(values, years, 0.95)
    p_value = stats.kendalltau(years, values).pvalue
    return float(slope), (float(low), float(high)), float(p_value)


def detect_years(monthly: list[float], slope: float) -> float:
    """Weatherhead et al. 1998; capped so a flat series stays readable."""
    sigma = float(np.std(monthly, ddof=1))
    phi = float(np.clip(np.corrcoef(monthly[:-1], monthly[1:])[0, 1], -0.9, 0.9))
    if abs(slope) < 1e-12:
        return 500.0
    n_star = ((3.3 * sigma / abs(slope)) * math.sqrt((1 + phi) / (1 - phi))) ** (2 / 3)
    return round(min(n_star, 500.0), 1)


def pettitt(years: list[int], values: list[float]) -> tuple[int, float, float, float, float] | None:
    """Pettitt (1979) change point on annual values: (year, K, p, mean_before, mean_after)."""
    n = len(values)
    if n < 8:
        return None
    signs = np.sign(np.subtract.outer(values, values))  # signs[j, i] = sign(x_j - x_i)
    u = [float(signs[t + 1 :, : t + 1].sum()) for t in range(n - 1)]
    t_best = int(np.argmax(np.abs(u)))
    k = abs(u[t_best])
    p_value = min(1.0, 2 * math.exp(-6 * k**2 / (n**3 + n**2)))
    before = float(np.mean(values[: t_best + 1]))
    after = float(np.mean(values[t_best + 1 :]))
    return years[t_best], k, p_value, before, after


def seasonal_slopes(rows: list[SeriesRow]) -> dict[str, float | None]:
    """Descriptive Sen slope per year for each season (DJF, MAM, JJA, SON)."""
    names = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM"}
    names.update({6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"})
    by_season: dict[str, dict[int, list[float]]] = {n: {} for n in ("DJF", "MAM", "JJA", "SON")}
    for row in rows:
        if row.anomaly is None:
            continue
        year = row.timestamp.year + (
            1 if row.timestamp.month == 12 else 0
        )  # December joins next DJF
        by_season[names[row.timestamp.month]].setdefault(year, []).append(row.anomaly)
    out: dict[str, float | None] = {}
    for season, per_year in by_season.items():
        years = sorted(y for y, v in per_year.items() if len(v) >= 2)
        if len(years) < 8:
            out[season] = None
            continue
        out[season] = round(
            float(stats.theilslopes([float(np.mean(per_year[y])) for y in years], years)[0]), 6
        )
    return out


@dataclass
class RawResult:
    spec: DatasetSpec
    region: RegionSpec
    rows: list[SeriesRow]
    withheld: bool
    slope: float | None
    ci: tuple[float, float] | None
    p_value: float | None
    effect: float | None
    detect: float | None
    sparkline: list[float]
    anomaly_years: dict[int, float]
    diagnostics: tuple[ChangePoint | None, SeasonalSlopes | None] = (None, None)


def analyse(spec: DatasetSpec, region: RegionSpec, rows: list[SeriesRow]) -> RawResult:
    withheld = region.region_id in spec.withheld_regions
    values = annual_means(rows, "value")
    sparkline = [round(values[y], 3) for y in sorted(values)]
    anomalies = annual_means(rows, "anomaly")
    if withheld:
        return RawResult(
            spec, region, rows, True, None, None, None, None, None, sparkline, anomalies
        )
    years = sorted(anomalies)
    series = [anomalies[y] for y in years]
    slope, ci, p_value = trend_stats(years, series)
    spread = float(np.std(series, ddof=1))
    effect = round(slope * (len(years) - 1) / spread, 2) if spread else None
    monthly = [r.anomaly for r in rows if r.anomaly is not None]
    found = pettitt(years, series)
    change_point = (
        ChangePoint(
            change_point_year=found[0],
            K=round(found[1], 3),
            p_value=round(found[2], 6),
            mean_before=round(found[3], 6),
            mean_after=round(found[4], 6),
            n=len(years),
        )
        if found
        else None
    )
    return RawResult(
        spec,
        region,
        rows,
        False,
        slope,
        ci,
        p_value,
        effect,
        detect_years(monthly, slope),
        sparkline,
        anomalies,
        (change_point, SeasonalSlopes(**seasonal_slopes(rows))),
    )


def build_trend(raw: RawResult, adjusted_p: float | None, family: str) -> TrendResult:
    spec, rows = raw.spec, raw.rows
    observed = sum(1 for r in rows if r.value is not None)
    common = {
        "dataset_id": spec.dataset_id,
        "variable_id": spec.variable_id,
        "region_id": raw.region.region_id,
        "period_start": dt.date(spec.start, 1, 1),
        "period_end": dt.date(spec.end, 12, 1),
        "series_used": "anomaly",
        "unit_per_year": spec.unit_per_year,
        "adjustment_method": "benjamini_hochberg",
        "observation_count": observed,
        "missing_month_count": len(rows) - observed,
        "mean_coverage_fraction": round(sum(r.coverage_fraction for r in rows) / len(rows), 4),
        "method": "SAMPLE: Mann–Kendall on annual means + Theil–Sen (fixture generator)",
        "serial_correlation_note": SAMPLE + ": not assessed",
        "caveats": [SAMPLE],
        "product_type": spec.product_type,
        "bh_family": family,
    }
    if raw.withheld:
        return TrendResult(
            **common,
            trend_direction="withheld",
            sen_slope_per_year=None,
            confidence_interval_95=None,
            p_value=None,
            adjusted_p_value=None,
            significant_at_0_05=False,
            withheld_reason="Result withheld: coverage below the minimum threshold.",
            verdict="not_enough_data",
            effect_size_swings=None,
            detect_years=None,
        )
    assert raw.slope is not None and raw.ci is not None and raw.p_value is not None
    assert adjusted_p is not None
    significant = adjusted_p < SIGNIFICANT
    if significant:
        direction = "increasing" if raw.slope > 0 else "decreasing"
    else:
        direction = "no_significant_trend"
    return TrendResult(
        **common,
        trend_direction=direction,
        sen_slope_per_year=round(raw.slope, 6),
        confidence_interval_95=(round(raw.ci[0], 6), round(raw.ci[1], 6)),
        p_value=round(raw.p_value, 6),
        adjusted_p_value=round(max(adjusted_p, round(raw.p_value, 6)), 6),
        significant_at_0_05=significant,
        withheld_reason=None,
        verdict=verdict_for(adjusted_p),
        effect_size_swings=raw.effect,
        detect_years=None if significant else raw.detect,
        change_point=raw.diagnostics[0],
        seasonal_slopes=raw.diagnostics[1],
    )


def build_windows(raw: RawResult) -> Windows:
    years = sorted(raw.anomaly_years)
    windows = []
    for start in years:
        for end in years:
            if end - start + 1 < MIN_WINDOW_YEARS:
                continue
            span = [y for y in years if start <= y <= end]
            if raw.withheld:
                windows.append(
                    Window(
                        start=start,
                        end=end,
                        sen_slope_per_year=None,
                        confidence_interval_95=None,
                        p_value=None,
                        adjusted_p_value=None,
                        verdict="not_enough_data",
                    )
                )
                continue
            slope, ci, p_value = trend_stats(span, [raw.anomaly_years[y] for y in span])
            adjusted = min(1.0, p_value * len(DATASETS))  # SAMPLE placeholder, not the real method
            windows.append(
                Window(
                    start=start,
                    end=end,
                    sen_slope_per_year=round(slope, 6),
                    confidence_interval_95=(round(ci[0], 6), round(ci[1], 6)),
                    p_value=round(p_value, 6),
                    adjusted_p_value=round(max(adjusted, round(p_value, 6)), 6),
                    verdict=verdict_for(adjusted),
                )
            )
    return Windows(
        dataset_id=raw.spec.dataset_id,
        region_id=raw.region.region_id,
        min_window_years=MIN_WINDOW_YEARS,
        windows=windows,
    )


def provenance_for(spec: DatasetSpec) -> Provenance:
    regions = {
        r.region_id: RegionProvenance(
            region_id=r.region_id,
            requested_box=",".join(str(c) for c in r.box),
            analyzable_region="n/a (synthetic)",
            giovanni_variable_id="n/a",
            permalink="https://example.invalid/sample",
            period_start=dt.date(spec.start, 1, 1),
            period_end=dt.date(spec.end, 12, 1),
            source_csv="n/a (generated)",
            source_csv_sha256="0" * 64,
            observations=(spec.end - spec.start + 1) * 12,
            transformations=["synthetic series with a known trend"],
        )
        for r in REGIONS
    }
    return Provenance(
        dataset_id=spec.dataset_id,
        product=SAMPLE,
        version="sample",
        doi_or_url="https://example.invalid/sample",
        access_date=dt.date(2026, 11, 14),
        access_route="sample (generated, not downloaded)",
        variable_field=spec.variable_id,
        scale_factor=1.0,
        native_unit=spec.unit,
        output_unit=spec.unit,
        spatial_resolution="sample",
        period_start=dt.date(spec.start, 1, 1),
        period_end=dt.date(spec.end, 12, 1),
        qa_rules=["none: synthetic data"],
        region_source="sample boxes from Linear doc 01",
        citation=SAMPLE,
        transformations=["synthetic series with a known trend"],
        regions=regions,
    )


def metadata_extras(spec: DatasetSpec) -> dict:
    return {
        "methodology": (
            f"{SAMPLE}. Synthetic series; trend by Kendall's tau and Theil-Sen on annual means."
        ),
        "limitations": [SAMPLE, "Illustrates the UI states only; no scientific meaning."],
        "attribution": SAMPLE,
    }


def write_json(path: Path, payload: object, indent: int | None = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload, indent=indent, ensure_ascii=False, separators=None if indent else (",", ":")
    )
    path.write_text(text + "\n", encoding="utf-8")


def box_polygon(box: tuple[float, float, float, float]) -> dict:
    w, s, e, n = box
    return {"type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]}


def generate(out_dir: Path) -> None:
    for name in ("processed", "results", "metadata"):
        shutil.rmtree(out_dir / name, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "data_version.txt").write_text(SAMPLE + "\n", encoding="utf-8")

    catalogue = [
        CatalogueItem(
            dataset_id=d.dataset_id,
            variable_id=d.variable_id,
            label=d.label,
            unit=d.unit,
            period_start=dt.date(d.start, 1, 1),
            period_end=dt.date(d.end, 12, 1),
            status="ready",
        )
        for d in DATASETS
    ]
    catalogue.append(
        CatalogueItem(
            dataset_id="sample_ndvi",
            variable_id="ndvi",
            label="Vegetation greenness (NDVI)",
            unit="unitless",
            period_start=dt.date(2001, 1, 1),
            period_end=dt.date(2025, 12, 1),
            status="coming_soon",
        )
    )
    write_json(out_dir / "catalogue.json", [c.model_dump(mode="json") for c in catalogue])

    regions = [
        Region(
            region_id=r.region_id,
            name=r.name,
            description=f"{SAMPLE}: sample region box.",
            geometry=box_polygon(r.box),
            source="sample boxes from Linear doc 01",
            licence="n/a (sample)",
        )
        for r in REGIONS
    ]
    write_json(out_dir / "regions.json", [r.model_dump(mode="json") for r in regions])

    raws: dict[tuple[str, str], RawResult] = {}
    for d_index, spec in enumerate(DATASETS):
        for r_index, region in enumerate(REGIONS):
            rng = np.random.default_rng(1000 + d_index * 10 + r_index)
            rows = make_series(spec, region, rng)
            raws[(spec.dataset_id, region.region_id)] = analyse(spec, region, rows)
            path = out_dir / "processed" / spec.dataset_id / f"{region.region_id}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            table = pa.Table.from_pylist([r.model_dump() for r in rows], schema=SERIES_SCHEMA)
            pq.write_table(table, path)

    for spec in DATASETS:
        write_json(
            out_dir / "processed" / spec.dataset_id / "provenance.json",
            provenance_for(spec).model_dump(mode="json"),
        )
        meta = Metadata(
            dataset_id=spec.dataset_id, provenance=provenance_for(spec), **metadata_extras(spec)
        )
        write_json(out_dir / "metadata" / f"{spec.dataset_id}.json", metadata_extras(spec))
        assert meta.dataset_id == spec.dataset_id

    # Compare family: one variable across regions -> results/<dataset_id>/trends.json
    for spec in DATASETS:
        live = [raws[(spec.dataset_id, r.region_id)] for r in REGIONS]
        tested = [x for x in live if not x.withheld]
        adjusted = dict(
            zip(
                [x.region.region_id for x in tested],
                benjamini_hochberg([x.p_value for x in tested]),  # type: ignore[misc]
                strict=True,
            )
        )
        family = f"compare:{spec.variable_id}"
        trends = [build_trend(x, adjusted.get(x.region.region_id), family) for x in live]
        write_json(
            out_dir / "results" / spec.dataset_id / "trends.json",
            [t.model_dump(mode="json") for t in trends],
        )

    # Lineup family: every variable in one region -> results/lineup/<region_id>.json
    for region in REGIONS:
        live = [raws[(d.dataset_id, region.region_id)] for d in DATASETS]
        tested = [x for x in live if not x.withheld]
        adjusted = dict(
            zip(
                [x.spec.dataset_id for x in tested],
                benjamini_hochberg([x.p_value for x in tested]),  # type: ignore[misc]
                strict=True,
            )
        )
        family = f"lineup:{region.region_id}"
        rows = []
        for x in live:
            trend = build_trend(x, adjusted.get(x.spec.dataset_id), family)
            rows.append(
                LineupRow(
                    dataset_id=x.spec.dataset_id,
                    variable_id=x.spec.variable_id,
                    label=x.spec.label,
                    definition=x.spec.definition,
                    product_type=x.spec.product_type,
                    period_start=trend.period_start,
                    period_end=trend.period_end,
                    sparkline=x.sparkline,
                    trend=trend,
                )
            )
        rows.sort(
            key=lambda row: (
                row.trend.adjusted_p_value is None,
                row.trend.adjusted_p_value or 0.0,
                -abs(row.trend.effect_size_swings or 0.0),
            )
        )
        lineup = Lineup(region_id=region.region_id, bh_family=family, rows=rows)
        write_json(
            out_dir / "results" / "lineup" / f"{region.region_id}.json",
            lineup.model_dump(mode="json"),
        )

    for (dataset_id, region_id), raw in raws.items():
        windows = build_windows(raw)
        write_json(
            out_dir / "results" / "windows" / dataset_id / f"{region_id}.json",
            windows.model_dump(mode="json"),
            indent=None,
        )


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    generate(root / "data" / "fixtures")
    print("fixtures written to", root / "data" / "fixtures")


if __name__ == "__main__":
    main()
