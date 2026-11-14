# analysis/

**Owner: Nandini.** The statistics module: anomalies, seasonal Mann–Kendall, Sen's slope, 95% confidence intervals, Benjamini–Hochberg correction, verdicts, effect size, Time Machine windows and detectability.

- Reads `data/processed/`, writes `data/results/` (trends, lineup and windows files; schemas in Linear doc 04).
- Method and wording rules: Linear doc "05 · Scientific Method & Validation". Results are checked against an independent implementation (`pymannkendall`).
- The frontend never computes statistics; everything it shows is written here first.
- No causal or predictive wording anywhere.

## Running it

```bash
python -m analysis.run                  # every region with processed data
python -m analysis.run --region ireland
python -m pytest analysis
```

Writes `data/results/<dataset_id>/trends.json`, `data/results/lineup/<region_id>.json` and `data/results/windows/<dataset_id>/<region_id>.json`. Each file is validated against the backend Pydantic models before it is written, so a contract break fails here rather than in the API.

Windows are fetched **per selection** by the frontend (one region x one variable, ~575 kB each); bundling all of them into the initial load would put ~14 MB in front of the judge.
