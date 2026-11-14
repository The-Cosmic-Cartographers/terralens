# AI use log

NASA Space Apps requires every AI tool used, and what it was used for, to be declared. Undeclared AI use is disqualifying. Add a row in the same pull request as the work.

| Date | Person | Tool | What it was used for | Files / areas |
| -- | -- | -- | -- | -- |
| 2026-11-14 | Kevin | Claude Code | Planning, project docs, initial repo structure | repo root, `.github/`, `backend/`, per-folder READMEs |
| 2026-11-14 | Kevin | Claude Code | Pydantic models and contract tests for the data/API contract (NAS-16) | `backend/app/models/`, `backend/tests/test_models.py` |
| 2026-11-14 | Kevin | Claude Code | SAMPLE fixtures generator, fixtures and fixture tests (NAS-17) | `backend/scripts/`, `data/fixtures/`, `backend/tests/test_fixtures.py` |
| 2026-11-14 | Kevin | Claude Code | API v1 part A: data store, error format, catalogue/regions/metadata endpoints and tests (NAS-18) | `backend/app/api/`, `backend/app/services/`, `backend/app/errors.py`, `backend/tests/test_api.py` |
| 2026-11-14 | Frontend team | Codex | App shell, React Router routes, central API/static data client, shared states, Recharts foundation and responsive styling (D11) | `frontend/nasa-earth-trends/src/`, `frontend/nasa-earth-trends/package.json`, `frontend/nasa-earth-trends/.env.example` |
| 2026-11-14 | Frontend team | Codex | Homepage investigation flow, five-region selector, MapLibre map shell, environmental variable explanations, Lineup guide and Delhi–Dublin NO₂ comparison frame | `frontend/nasa-earth-trends/src/`, `frontend/nasa-earth-trends/package.json` |

AI-generated images or video must carry a visible "AI-generated" watermark. No NASA logos or branding in AI-generated output.
