# analysis/

**Owner: Nandini.** The statistics module: anomalies, seasonal Mann–Kendall, Sen's slope, 95% confidence intervals, Benjamini–Hochberg correction, verdicts, effect size, Time Machine windows and detectability.

- Reads `data/processed/`, writes `data/results/` (trends, lineup and windows files; schemas in Linear doc 04).
- Method and wording rules: Linear doc "05 · Scientific Method & Validation". Results are checked against an independent implementation (`pymannkendall`).
- The frontend never computes statistics; everything it shows is written here first.
- No causal or predictive wording anywhere.
