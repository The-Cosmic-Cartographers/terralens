# pipeline/

**Owner: Parth.** Retrieval and regional aggregation: raw NASA series (Giovanni area-averaged CSV, or GES DISC subsets) become one clean monthly series per place and variable.

- Writes `data/processed/<dataset_id>/<region_id>.parquet` and `provenance.json` next to it (schema in Linear doc 04).
- Raw downloads go in `data/raw/` and are never committed.
- Every series carries units, coverage and the product/version it came from. Convert units here (K to °C, kg m-2 s-1 to mm/day) and cut every series at 2025-12-31.
- Giovanni snaps boxes to the grid and reports an "analyzable region": record it in `provenance.json`.
- Tests go next to the code as `test_*.py`.
