"""Geometry, resolution parsing and the small-region warning."""

from __future__ import annotations

from terralens.regions import BBox, Region, get_region, parse_resolution


def test_parse_resolution_handles_all_registry_forms():
    assert parse_resolution("0.25°") == (0.25, 0.25)
    assert parse_resolution("0.1°") == (0.1, 0.1)
    assert parse_resolution("0.5° x 0.625°") == (0.5, 0.625)


def test_bbox_geojson_is_a_closed_polygon():
    feature = BBox(-10.5, 51.4, -6.0, 55.4).to_geojson()
    assert feature["type"] == "Feature"
    ring = feature["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1]
    assert len(ring) == 5


def test_region_geojson_carries_its_id():
    feature = get_region("ireland").to_geojson()
    assert feature["properties"]["region_id"] == "ireland"


def test_cell_estimate_uses_the_registry_resolution():
    coverage = get_region("ireland").cells("soil_moisture_0_10")
    assert coverage.cells > 100
    assert coverage.warn is False
    coarse = get_region("ireland").cells("t2m")
    assert coarse.cells < coverage.cells
    assert (coarse.lat_resolution, coarse.lon_resolution) == (0.5, 0.625)


def test_a_sub_cell_box_warns():
    tiny = Region(
        {
            "region_id": "tiny",
            "name": "Tiny box",
            "west": 0.0,
            "south": 0.0,
            "east": 0.1,
            "north": 0.1,
            "scope": "all",
        }
    )
    coverage = tiny.cells("t2m")
    assert coverage.warn is True
    assert "point sample" in coverage.detail or "below 4 cells" in coverage.detail


def test_a_region_is_one_registry_entry():
    payload = {
        "region_id": "testland",
        "name": "Testland",
        "west": 10.0,
        "south": 10.0,
        "east": 12.0,
        "north": 12.0,
        "scope": "all",
    }
    region = Region(payload)
    assert region.bbox.width == 2.0
    assert "testland" in region.info()
