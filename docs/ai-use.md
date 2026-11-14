# AI use log

NASA Space Apps requires every AI tool used, and what it was used for, to be declared. Undeclared AI use is disqualifying. Add a row in the same pull request as the work.

| Date | Person | Tool | What it was used for | Files / areas |
| -- | -- | -- | -- | -- |
| 2026-11-14 | Kevin | Claude Code | Planning, project docs, initial repo structure | repo root, `.github/`, `backend/`, per-folder READMEs |
| 2026-11-14 | Kevin | Claude Code | Pydantic models and contract tests for the data/API contract (NAS-16) | `backend/app/models/`, `backend/tests/test_models.py` |
| 2026-11-14 | Kevin | Claude Code | SAMPLE fixtures generator, fixtures and fixture tests (NAS-17) | `backend/scripts/`, `data/fixtures/`, `backend/tests/test_fixtures.py` |
| 2026-11-14 | Kevin | Claude Code | API v1 part A: data store, error format, catalogue/regions/metadata endpoints and tests (NAS-18) | `backend/app/api/`, `backend/app/services/`, `backend/app/errors.py`, `backend/tests/test_api.py` |
| 2026-11-14 | Kevin | Claude Code | API v1 part B: series, trend, lineup, windows endpoints, region 404 and tests (NAS-20) | `backend/app/api/v1.py`, `backend/app/services/store.py`, `backend/app/errors.py`, `backend/tests/test_api_regions.py` |
| 2026-11-14 | Kevin | Claude Code | Static JSON export `app.export` and tests (NAS-21) | `backend/app/export.py`, `backend/tests/test_export.py`, `backend/README.md` |
| 2026-11-14 | Kevin | Claude Code | `/compare` endpoint, store method, export of `compare/` and tests (NAS-23) | `backend/app/api/v1.py`, `backend/app/services/store.py`, `backend/app/export.py`, `backend/tests/test_compare.py` |
| 2026-11-14 | Kevin | Claude Code | Drafted the Linear project docs 00–12, task list, plan page, architecture diagram and judging Q&A; checked Giovanni availability and request timing through browser automation (no NASA data was saved or committed) | Linear, not in the repo |
| 2026-11-14 | Kevin | Claude Code | README rewrite (NAS-38) | `README.md`, `docs/ai-use.md` |
| 2026-11-14 | Kevin | Claude Code | Snapshot verifier, repo hygiene tests and a secrets/raw-file scan of the repo and git history (NAS-37) | `backend/app/verify_snapshot.py`, `backend/tests/test_verify_snapshot.py`, `backend/tests/test_repo_hygiene.py`, `backend/README.md` |
| 2026-11-14 | Parth | Codebuff (Buffy) | Pipeline v0: Giovanni CSV parsing, unit conversion, contract Parquet and provenance output, tests | `pipeline/` |
| 2026-11-14 | Kevin | Claude Code | Repo updated for the Vite + React frontend: env var, CORS default port, ignore rules, README | `.env.example`, `.gitignore`, `README.md`, `backend/app/config.py`, `backend/tests/test_api.py` |
| 2026-11-14 | Parth | Codebuff (Buffy) | NAS-5: D19 Iberia box and NW South Asia label fixes, aerosol row in the variable registry | `pipeline/regions.json`, `pipeline/registry.py` |
| 2026-11-14 | Kevin | Claude Code | Contract update: optional series coverage, per-region provenance, pipeline-to-API integration tests, review of PR #11 (NAS-16) | `backend/app/models/`, `backend/scripts/generate_fixtures.py`, `data/fixtures/`, `backend/tests/` |
| 2026-11-14 | Parth | Codebuff (Buffy) | NAS-56: Kevin's NAS-7 review fixes — per-variable windows, CSV unit-row guard, missing months kept as null rows, with tests | `pipeline/build.py`, `pipeline/giovanni.py`, `pipeline/registry.py`, `pipeline/tests/` |
| 2026-11-14 | Parth | Codebuff (Buffy) | NAS-6: T2M 1981–2025 for Ireland, Sahel and US Southwest, pulled from the NASA POWER regional API (MERRA-2) and built into processed series; added `--access-route` so provenance names the real access path | `data/raw/` (git-ignored), `data/processed/merra2_m2tmnxslv/`, `pipeline/build.py` |
| 2026-11-14 | Kevin | Claude Code | Pulled three T2M series through the Giovanni web UI with browser automation and fixed the pipeline parser for real Giovanni dates (NAS-6) | `pipeline/giovanni.py`, `pipeline/tests/`, `data/processed/merra2_m2tmnxslv/` |
| 2026-11-14 | Kevin | Claude Code | Index builder for the real data folder (catalogue, regions, metadata, data version), unique GLDAS dataset ids in the registry, and tests (NAS-6) | `backend/scripts/build_data_index.py`, `backend/tests/test_data_index.py`, `data/catalogue.json`, `data/regions.json`, `data/metadata/`, `pipeline/registry.py` |
| 2026-11-14 | Kevin | Claude Code | Contract update for D25 diagnostics (`change_point`, `seasonal_slopes`) in the models, fixture generator, fixtures and tests | `backend/app/models/results.py`, `backend/scripts/generate_fixtures.py`, `data/fixtures/`, `backend/tests/test_models.py` |
| 2026-11-14 | Kevin | Claude Code | Checked Giovanni's user manual for what it does and does not offer; reworded the one-line pitch ("chart") in the README and Linear docs | `README.md`, Linear docs 00, 01, 07, 09, 12, 13 |
| 2026-11-14 | Parth | Codebuff (Buffy) | NAS-43: generate the References list from `provenance.json` and `pyproject.toml` — dataset citations with Giovanni permalinks, software list, methods papers, and an explicit "not used, not cited" list — with tests | `pipeline/references.py`, `pipeline/tests/test_references.py`, `docs/references.md` |
| 2026-11-14 | Parth | Codebuff (Buffy) | NAS-57: pinned the IMERG row to the V07B reprocessed run after confirming the granule filenames carry `.V07B` | `pipeline/registry.py` |


| 2026-11-14 | Parth | Codebuff (Buffy) | NAS-8: exploratory checks and plots for the three T2M series — coverage, gaps, spikes, seasonal cycle, anomalies, Sen slope and Mann-Kendall used only to compare direction with doc 11 §3 | `pipeline/eda.py`, `pipeline/tests/test_eda.py`, `.gitignore` |
| 2026-11-14 | Kevin | Claude Code | Pointed CI and the export defaults at the frontend's real folder (`frontend/nasa-earth-trends`) | `.github/workflows/ci.yml`, `backend/app/export.py`, `backend/app/verify_snapshot.py`, READMEs |
| 2026-11-14 | Nandini | Codebuff (Buffy) | Statistics module: anomalies, seasonal Mann–Kendall, Hamed–Rao correction, Sen's slope and 95% CI, Benjamini–Hochberg, verdicts, effect size, detectability, Pettitt change point and seasonal slopes, with known-answer and pymannkendall cross-checks (NAS-10, NAS-11, NAS-28, NAS-46) | `analysis/stats.py`, `analysis/test_stats.py` |
| 2026-11-14 | Nandini | Codebuff (Buffy) | Time Machine windows: every start/end pair at least ten years, incremental S matching a direct recomputation, and the full-window coverage guard that skips windows spanning a dropped year (NAS-29, NAS-59 equivalent) | `analysis/windows.py`, `analysis/test_windows.py` |
| 2026-11-14 | Nandini | Codebuff (Buffy) | Pipeline runner from processed Parquet to contract-valid results, including the two BH families — lineup per region and compare per variable across regions — and the ranked lineup (NAS-12, NAS-28, NAS-30) | `analysis/run.py`, `analysis/test_compare_family.py`, `data/results/` |
| 2026-11-14 | Nandini | Codebuff (Buffy) | Sensitivity and scientific QA material generated from the real series rather than typed by hand, and the methodology, uncertainty and limitations copy for the app and project page (NAS-47, NAS-48, NAS-49) | `analysis/sensitivity.py`, `analysis/qa.py`, `docs/sensitivity-notes.md`, `docs/qa-report.md`, `docs/methodology.md` |
| 2026-11-14 | Nandini | Codebuff (Buffy) | Decision records and contract wording in Linear: D25 diagnostics proposal and acceptance, and the schema 2 additions (NAS-9, NAS-16) | Linear docs 10 and 04, not in the repo |
| 2026-11-14 | Kevin | Claude Code | Wrote the first real static snapshot into the frontend's public folder and fixed the hygiene test's path (NAS-21, NAS-22) | `frontend/nasa-earth-trends/public/data/`, `backend/tests/test_repo_hygiene.py` |
| 2026-11-14 | Kevin | Claude Code | Cloudflare Workers static-assets config for the frontend (NAS-22) | `frontend/nasa-earth-trends/wrangler.jsonc` |
| 2026-11-14 | Kevin | Claude Code | First Cloudflare Workers deploy of the static app and the live URL in the README (NAS-22) | `README.md`, deployment (no files) |
| 2026-11-14 | Kevin | Claude Code | Wording fixes to the Case Files (D25, overclaim, provisional note) and an unverified-claims banner on the 1.5 °C card | `docs/case-files.md`, `docs/baseline-and-thresholds.md` |
| 2026-11-14 | Parth | Codebuff (Buffy) | NAS-60: `pipeline.pull` — one command that plans per-variable routes, pulls Harmony subsets with resumable checkpoints and capped retries under a time budget, builds the processed series, and reports blocked rows instead of substituting data; tests for planning, resume, retry cap, deadline and CSV hand-off | `pipeline/pull.py`, `pipeline/tests/test_pull.py`, `pipeline/README.md`, `pyproject.toml` |

| 2026-11-14 | Parth | Codebuff (Buffy) | NAS-60: centre-in-box footprint in `month_means` so a Harmony pull averages Giovanni's cells (T2M Ireland went from 0.88 °C to 0.0005 °C against Giovanni), `slice_extent` writing the averaged footprint into provenance as `analyzable_region`, and the checkpoint carrying it across runs; tests for the mask, the extent and the hand-off | `pipeline/pull.py`, `pipeline/tests/test_pull.py`, `pipeline/README.md` |

Parth, Nandini and Bhargav: add a row for every AI tool you use, including chat assistants, code completion and image tools, in the same pull request as the work.

AI-generated images or video must carry a visible "AI-generated" watermark. No NASA logos or branding in AI-generated output.
