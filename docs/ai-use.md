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

AI-generated images or video must carry a visible "AI-generated" watermark. No NASA logos or branding in AI-generated output.
