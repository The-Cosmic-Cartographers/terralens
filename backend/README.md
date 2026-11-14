# backend/

**Owner: Kevin.** FastAPI app that serves the processed series and results, and the `export` command that writes the same JSON as a static snapshot for the deployed frontend.

- Schemas and endpoints: Linear doc "04 · Data & API Contracts" (the contract is fixed; changes need the consumer's agreement).
- Layout: `app/main.py` (entry), `app/api/` (routes), `app/models/` (Pydantic models), `app/services/` (reading `data/`).
- Reads files from `data/processed/` and `data/results/`. It never computes statistics.
- Run: `uv run uvicorn app.main:app --app-dir backend --reload`

## Endpoints so far (API v1)

`GET /health` · `GET /api/v1/catalogue` · `GET /api/v1/regions` · `GET /api/v1/metadata?dataset_id=`

Per region: `GET /api/v1/regions/{region_id}/series?dataset_id=` · `/trend?dataset_id=` · `/lineup` · `/windows?dataset_id=`

Across regions: `GET /api/v1/compare?dataset_id=` (one variable, every region, compare-family BH adjustment read from `results/<dataset_id>/trends.json`; `period_note` is set when regions' periods differ and the reported period is their overlap). Its adjusted p-values come from a different family than the Lineup's, so a region can read differently in the two views.

`/trend` returns the lineup-family result, so the detail card always matches the Lineup row. A withheld result is 200 with `trend_direction: "withheld"`.

Errors use the doc 04 format: 404 `region_not_found` / `dataset_not_found`, 422 `invalid_parameter`, 503 `data_unavailable` (a file is missing, unreadable, or fails its model).

## Data folder

The API reads `TERRALENS_DATA_DIR` (default `./data`). Point it at the SAMPLE fixtures to build before real data exists:

```bash
TERRALENS_DATA_DIR=./data/fixtures uv run uvicorn app.main:app --app-dir backend --reload
```

## Static export (NAS-21)

The deployed app reads static JSON, not a live server. The export writes every API response to the doc 04 §5 paths, using the same store as the API.

```bash
# real data (refuses if data_version contains SAMPLE)
PYTHONPATH=backend uv run python -m app.export

# local development with the SAMPLE fixtures
PYTHONPATH=backend uv run python -m app.export --data-dir data/fixtures --allow-sample
```

Options: `--data-dir` (default `TERRALENS_DATA_DIR` or `./data`), `--out` (default `frontend/public/data`), `--allow-sample`.

- Writes `health.json` (carries `data_version`), `catalogue.json`, `regions.json`, `metadata/`, `lineup/`, `series/`, `trend/`, `windows/`, `compare/`.
- All files are checked first; if any ready dataset × region is missing or invalid it exits 1 and writes nothing.
- Only those generated names are replaced. Other files in the output folder are left alone.
- Output is deterministic, so re-running on the same data gives identical files.
