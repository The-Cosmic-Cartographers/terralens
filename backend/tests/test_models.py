"""Contract tests for the doc 04 models.

Every record below is a labelled SAMPLE: it exists to exercise the schemas and
must never be shown as a finding.
"""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.models import (
    CatalogueItem,
    CompareResult,
    ErrorResponse,
    Health,
    Lineup,
    Metadata,
    Provenance,
    Region,
    SeriesResponse,
    SeriesRow,
    TrendResult,
    Windows,
)

SAMPLE = "SAMPLE — NOT NASA DATA"


def series_row(**overrides):
    row = {
        "dataset_id": "sample_t2m",
        "variable_id": "t2m",
        "region_id": "ireland",
        "timestamp": "2020-01-01",
        "value": 6.1,
        "unit": "°C",
        "anomaly": 0.4,
        "valid_cell_count": 245,
        "total_cell_count": 269,
        "coverage_fraction": 0.91,
        "quality_summary": "sample",
        "source": SAMPLE,
    }
    row.update(overrides)
    return row


def trend(**overrides):
    result = {
        "dataset_id": "sample_t2m",
        "variable_id": "t2m",
        "region_id": "ireland",
        "period_start": "1981-01-01",
        "period_end": "2025-12-01",
        "series_used": "anomaly",
        "trend_direction": "increasing",
        "sen_slope_per_year": 0.031,
        "unit_per_year": "°C/yr",
        "confidence_interval_95": [0.012, 0.049],
        "p_value": 0.004,
        "adjusted_p_value": 0.01,
        "adjustment_method": "benjamini_hochberg",
        "significant_at_0_05": True,
        "observation_count": 540,
        "missing_month_count": 0,
        "mean_coverage_fraction": 0.99,
        "method": "seasonal_mann_kendall + sens_slope",
        "serial_correlation_note": SAMPLE,
        "caveats": [SAMPLE],
        "withheld_reason": None,
        "product_type": "reanalysis",
        "bh_family": "lineup:ireland",
        "verdict": "significant",
        "effect_size_swings": 2.4,
        "detect_years": None,
    }
    result.update(overrides)
    return result


def weak_trend(**overrides):
    return trend(
        trend_direction="no_significant_trend",
        p_value=0.03,
        adjusted_p_value=0.07,
        significant_at_0_05=False,
        verdict="weak_evidence",
        detect_years=31.0,
        **overrides,
    )


def withheld_trend(**overrides):
    return trend(
        trend_direction="withheld",
        sen_slope_per_year=None,
        confidence_interval_95=None,
        p_value=None,
        adjusted_p_value=None,
        significant_at_0_05=False,
        verdict="not_enough_data",
        effect_size_swings=None,
        withheld_reason="Result withheld: coverage below the minimum threshold.",
        **overrides,
    )


def lineup_row(variable_id="t2m", **trend_overrides):
    return {
        "dataset_id": "sample_t2m",
        "variable_id": variable_id,
        "label": "Air temperature (2 m)",
        "definition": "How warm the air is at about head height",
        "product_type": "reanalysis",
        "period_start": "1981-01-01",
        "period_end": "2025-12-01",
        "sparkline": [0.1, 0.2, 0.3],
        "trend": trend(variable_id=variable_id, **trend_overrides),
    }


def provenance(**overrides):
    record = {
        "dataset_id": "sample_t2m",
        "product": SAMPLE,
        "version": "sample",
        "doi_or_url": "https://example.invalid/sample",
        "access_date": "2026-11-14",
        "access_route": "sample",
        "variable_field": "T2M",
        "scale_factor": 1.0,
        "native_unit": "K",
        "output_unit": "°C",
        "spatial_resolution": "0.5 x 0.625 deg",
        "period_start": "1981-01-01",
        "period_end": "2025-12-01",
        "qa_rules": ["sample"],
        "region_source": "sample",
        "citation": SAMPLE,
        "regions": {
            "ireland": {
                "region_id": "ireland",
                "requested_box": "-10.5,51.4,-6.0,55.4",
                "analyzable_region": "sample",
                "giovanni_variable_id": "sample",
                "permalink": "https://example.invalid/sample",
                "period_start": "1981-01-01",
                "period_end": "2025-12-01",
                "source_csv": "sample.csv",
                "source_csv_sha256": "a" * 64,
                "observations": 540,
                "transformations": ["monthly aggregation"],
            }
        },
        "transformations": ["monthly aggregation"],
    }
    record.update(overrides)
    return record


def window(**overrides):
    record = {
        "start": 1981,
        "end": 2025,
        "sen_slope_per_year": 0.03,
        "confidence_interval_95": [0.01, 0.05],
        "p_value": 0.01,
        "adjusted_p_value": 0.02,
        "verdict": "significant",
    }
    record.update(overrides)
    return record


# --- series --------------------------------------------------------------


def test_series_row_accepts_a_sample_row():
    assert SeriesRow(**series_row()).coverage_fraction == 0.91


def test_series_row_value_can_be_withheld():
    assert SeriesRow(**series_row(value=None, anomaly=None)).value is None


def test_series_row_coverage_may_be_null_when_the_source_has_no_cell_counts():
    row = SeriesRow(
        **series_row(valid_cell_count=None, total_cell_count=None, coverage_fraction=None)
    )
    assert row.coverage_fraction is None


def test_series_row_may_omit_the_coverage_columns_entirely():
    record = series_row()
    for name in ("valid_cell_count", "total_cell_count", "coverage_fraction"):
        del record[name]
    assert SeriesRow(**record).valid_cell_count is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"total_cell_count": None},  # counts must come as a pair
        {"coverage_fraction": None},  # counts given, fraction missing
        {"timestamp": "2020-01-15"},  # not the first of the month
        {"coverage_fraction": 0.5},  # not valid / total
        {"valid_cell_count": 300},  # more valid cells than cells
        {"unit": ""},
        {"region_id": "Ireland"},  # not a snake_case slug
        {"surprise": 1},  # unknown field
    ],
)
def test_series_row_rejects_contract_violations(overrides):
    with pytest.raises(ValidationError):
        SeriesRow(**series_row(**overrides))


def test_series_response_rows_must_match_the_response():
    ok = {
        "dataset_id": "sample_t2m",
        "variable_id": "t2m",
        "region_id": "ireland",
        "unit": "°C",
        "rows": [series_row()],
    }
    assert SeriesResponse(**ok).rows
    with pytest.raises(ValidationError):
        SeriesResponse(**{**ok, "unit": "K"})
    with pytest.raises(ValidationError):
        SeriesResponse(**{**ok, "region_id": "sahel"})


# --- provenance -----------------------------------------------------------


def test_provenance_accepts_a_sample_record():
    record = Provenance(**provenance())
    assert record.regions["ireland"].analyzable_region == "sample"


def test_provenance_requires_the_product_fields():
    record = provenance()
    del record["access_route"]
    with pytest.raises(ValidationError):
        Provenance(**record)


def test_provenance_citation_may_be_left_for_later():
    record = provenance()
    del record["citation"]
    assert Provenance(**record).citation == ""


def test_provenance_holds_several_regions_and_needs_at_least_one():
    record = provenance()
    second = {**record["regions"]["ireland"], "region_id": "iberia"}
    record["regions"]["iberia"] = second
    assert set(Provenance(**record).regions) == {"ireland", "iberia"}
    record["regions"] = {}
    with pytest.raises(ValidationError):
        Provenance(**record)


def test_provenance_region_key_must_match_its_region_id():
    record = provenance()
    record["regions"]["iberia"] = record["regions"].pop(
        "ireland"
    )  # key says iberia, id says ireland
    with pytest.raises(ValidationError):
        Provenance(**record)


def test_provenance_region_fields_are_required_and_unknown_ones_rejected():
    record = provenance()
    del record["regions"]["ireland"]["requested_box"]
    with pytest.raises(ValidationError):
        Provenance(**record)
    record = provenance()
    record["regions"]["ireland"]["extra"] = 1
    with pytest.raises(ValidationError):
        Provenance(**record)


# --- trend ----------------------------------------------------------------


def test_trend_accepts_significant_weak_and_withheld_results():
    assert TrendResult(**trend()).verdict == "significant"
    assert TrendResult(**weak_trend()).verdict == "weak_evidence"
    assert TrendResult(**withheld_trend()).trend_direction == "withheld"


@pytest.mark.parametrize(
    "overrides",
    [
        {"adjusted_p_value": 0.2},  # verdict says significant, adjusted p says no
        {"p_value": 0.5},  # raw p above adjusted p
        {"sen_slope_per_year": -0.03},  # increasing needs a positive slope
        {"confidence_interval_95": [0.05, 0.01]},  # unordered
        {"detect_years": 20.0},  # only for non-significant verdicts
        {"significant_at_0_05": False},
        {"trend_direction": "no_significant_trend"},
        {"period_end": "1970-01-01"},
        {"bh_family": "everything"},
    ],
)
def test_trend_rejects_contract_violations(overrides):
    with pytest.raises(ValidationError):
        TrendResult(**trend(**overrides))


def test_withheld_trend_must_null_its_statistics():
    for change in (
        {"p_value": 0.01},
        {"withheld_reason": None},
        {"verdict": "no_clear_trend"},
        {"effect_size_swings": 1.0},
    ):
        with pytest.raises(ValidationError):
            TrendResult(**{**withheld_trend(), **change})


def test_non_withheld_trend_needs_its_statistics():
    with pytest.raises(ValidationError):
        TrendResult(**trend(adjusted_p_value=None))
    with pytest.raises(ValidationError):
        TrendResult(**trend(withheld_reason="because"))


# --- lineup, windows, compare ----------------------------------------------


def test_lineup_accepts_rows_in_one_region_and_family():
    lineup = {
        "region_id": "ireland",
        "bh_family": "lineup:ireland",
        "rows": [lineup_row(), lineup_row("soil_moisture_0_10cm")],
    }
    assert len(Lineup(**lineup).rows) == 2


def test_lineup_rejects_mixed_regions_and_families():
    row = lineup_row()
    with pytest.raises(ValidationError):
        Lineup(region_id="sahel", bh_family="lineup:sahel", rows=[row])
    with pytest.raises(ValidationError):
        Lineup(region_id="ireland", bh_family="compare:t2m", rows=[row])


def test_lineup_row_must_match_its_trend():
    row = deepcopy(lineup_row())
    row["variable_id"] = "precipitation"
    with pytest.raises(ValidationError):
        Lineup(region_id="ireland", bh_family="lineup:ireland", rows=[row])
    row = lineup_row()
    row["product_type"] = "satellite"
    with pytest.raises(ValidationError):
        Lineup(region_id="ireland", bh_family="lineup:ireland", rows=[row])


def test_windows_accept_whole_year_windows_of_the_minimum_length():
    record = {
        "dataset_id": "sample_t2m",
        "region_id": "ireland",
        "min_window_years": 10,
        "windows": [window(), window(start=2000, end=2009)],
    }
    assert len(Windows(**record).windows) == 2
    record["windows"].append(window(start=2000, end=2005))  # only 6 years
    with pytest.raises(ValidationError):
        Windows(**record)


def test_window_with_a_verdict_needs_statistics():
    with pytest.raises(ValidationError):
        Windows(
            dataset_id="sample_t2m",
            region_id="ireland",
            min_window_years=10,
            windows=[window(p_value=None)],
        )
    empty = window(
        sen_slope_per_year=None,
        confidence_interval_95=None,
        p_value=None,
        adjusted_p_value=None,
        verdict="not_enough_data",
    )
    assert Windows(
        dataset_id="sample_t2m", region_id="ireland", min_window_years=10, windows=[empty]
    )


def test_compare_results_share_one_variable_and_family():
    family = "compare:t2m"
    compare = {
        "dataset_id": "sample_t2m",
        "variable_id": "t2m",
        "period_start": "1981-01-01",
        "period_end": "2025-12-01",
        "period_note": None,
        "bh_family": family,
        "results": [
            trend(bh_family=family),
            trend(region_id="iberia", bh_family=family, sen_slope_per_year=0.05),
        ],
    }
    assert len(CompareResult(**compare).results) == 2
    compare["bh_family"] = "compare:precipitation"
    with pytest.raises(ValidationError):
        CompareResult(**compare)


# --- catalogue, region, metadata, health, error -----------------------------


def test_catalogue_item_status_is_ready_or_coming_soon():
    item = {
        "dataset_id": "sample_t2m",
        "variable_id": "t2m",
        "label": "Air temperature (2 m)",
        "unit": "°C",
        "period_start": "1981-01-01",
        "period_end": "2025-12-01",
        "status": "ready",
    }
    assert CatalogueItem(**item).status == "ready"
    with pytest.raises(ValidationError):
        CatalogueItem(**{**item, "status": "maybe"})


def test_region_needs_a_geometry_or_a_url():
    base = {
        "region_id": "ireland",
        "name": "Ireland",
        "description": "",
        "source": "s",
        "licence": "l",
    }
    polygon = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
    assert Region(**base, geometry=polygon).geometry == polygon
    assert Region(**base, geometry_url="https://example.invalid/ireland.geojson")
    with pytest.raises(ValidationError):
        Region(**base)


def test_metadata_provenance_must_match_its_dataset():
    record = {
        "dataset_id": "sample_t2m",
        "provenance": provenance(),
        "methodology": "sample",
        "limitations": ["sample"],
        "attribution": "sample",
    }
    assert Metadata(**record).dataset_id == "sample_t2m"
    record["provenance"] = provenance(dataset_id="sample_precip")
    with pytest.raises(ValidationError):
        Metadata(**record)


def test_health_and_error_shapes():
    assert Health(status="ok", data_version="sample").status == "ok"
    with pytest.raises(ValidationError):
        Health(status="degraded", data_version="x")
    error = {
        "error": {"code": "region_not_found", "message": "Unknown region_id 'xyz'", "details": {}}
    }
    assert ErrorResponse(**error).error.code == "region_not_found"
    error["error"]["code"] = "result_withheld"  # doc 04: not used
    with pytest.raises(ValidationError):
        ErrorResponse(**error)
