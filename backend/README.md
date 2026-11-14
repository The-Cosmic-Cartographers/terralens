# backend/

**Owner: Kevin.** FastAPI app that serves the processed series and results, and the `export` command that writes the same JSON as a static snapshot for the deployed frontend.

- Schemas and endpoints: Linear doc "04 · Data & API Contracts" (the contract is fixed; changes need the consumer's agreement).
- Layout: `app/main.py` (entry), `app/api/` (routes), `app/models/` (Pydantic models), `app/services/` (reading `data/`).
- Reads files from `data/processed/` and `data/results/`. It never computes statistics.
- Run: `uv run uvicorn app.main:app --app-dir backend --reload`
