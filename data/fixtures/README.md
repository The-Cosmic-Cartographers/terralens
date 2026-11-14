# data/fixtures/

**SAMPLE data. Every value here is made up. None of it is NASA data and none of it is a finding.**

Fixtures let the frontend and backend build in parallel before real data exists. They have the exact shapes of the real files (Linear doc 04) and the same folder layout as `data/`, so the backend reads them by pointing at this folder:

```bash
TERRALENS_DATA_DIR=./data/fixtures uv run uvicorn app.main:app --app-dir backend --reload
```

## What is in it

2 regions (`ireland`, `iberia`) × 5 sample datasets that mirror the Lineup rows. The synthetic trends are tuned so every UI state appears:

| State | Where |
| -- | -- |
| Significant, increasing | `t2m` in both regions; `precipitation` in Ireland |
| Significant, decreasing | `precipitation` and `soil_moisture_0_10cm` in Iberia |
| Weak evidence | `aerosol_optical_depth` in Ireland |
| No clear trend (with detectability years) | `soil_moisture_0_10cm`, `evapotranspiration` in Ireland; `evapotranspiration` in Iberia |
| Withheld ("not enough data") | `aerosol_optical_depth` in Iberia |
| Opposite arrows between regions | `precipitation` (Ireland up, Iberia down) |
| Dataset that is not ready | `sample_ndvi` in the catalogue (`coming_soon`) |

Datasets have different windows on purpose (temperature 1981–2025, soil moisture and evapotranspiration 2000–2025, precipitation 2001–2024, aerosol 2003–2025), like the real ones.

## Layout

```
data_version.txt                          "SAMPLE — NOT NASA DATA"
catalogue.json                            list of catalogue items
regions.json                              list of regions (GeoJSON box geometry)
metadata/<dataset_id>.json                methodology, limitations, attribution
processed/<dataset_id>/<region_id>.parquet   schema 1, one row per month
processed/<dataset_id>/provenance.json
results/<dataset_id>/trends.json          compare family: one result per region
results/lineup/<region_id>.json           lineup family: the ranked board
results/windows/<dataset_id>/<region_id>.json   Time Machine windows
```

## The SAMPLE banner

Every series row carries `"source": "SAMPLE — NOT NASA DATA"`, `/health` returns that string as `data_version`, and `/metadata` returns it as the provenance `product`. The UI shows a visible **SAMPLE DATA** banner whenever any of those contains `SAMPLE`.

## Regenerating

The files are written by a deterministic generator and a test checks they match it:

```bash
PYTHONPATH=backend uv run python -m scripts.generate_fixtures
```

## Before the demo

Fixtures must be gone from the deployed demo before Sunday 16:00 (milestone M5). The deployed snapshot must come only from `data/processed` and `data/results`.
