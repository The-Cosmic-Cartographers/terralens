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

Parth, Nandini and Bhargav: add a row for every AI tool you use, including chat assistants, code completion and image tools, in the same pull request as the work.

AI-generated images or video must carry a visible "AI-generated" watermark. No NASA logos or branding in AI-generated output.
