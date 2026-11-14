# backend/

**Owner: Kevin.** FastAPI app that serves the processed series and results, and the `export` command that writes the same JSON as a static snapshot for the deployed frontend.

- Schemas and endpoints: Linear doc "04 · Data & API Contracts" (the contract is fixed; changes need the consumer's agreement).
- Layout: `app/main.py` (entry), `app/api/` (routes), `app/models/` (Pydantic models), `app/services/` (reading `data/`).
- Reads files from `data/processed/` and `data/results/`. It never computes statistics.
- Run: `uv run uvicorn app.main:app --app-dir backend --reload`

## Endpoints so far (API v1, part A)

`GET /health` · `GET /api/v1/catalogue` · `GET /api/v1/regions` · `GET /api/v1/metadata?dataset_id=`

Errors use the doc 04 format: 404 `dataset_not_found`, 422 `invalid_parameter`, 503 `data_unavailable` (a file is missing or fails its model).

## Data folder

The API reads `TERRALENS_DATA_DIR` (default `./data`). Point it at the SAMPLE fixtures to build before real data exists:

```bash
TERRALENS_DATA_DIR=./data/fixtures uv run uvicorn app.main:app --app-dir backend --reload
```
