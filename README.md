# TerraLens

**Other tools test the trend you already suspected. TerraLens finds the suspects.**

TerraLens is an Earth-system trend discovery tool built for the NASA Space Apps Challenge 2026, *Be An Earth System Trend Detective!*. Pick a place and it scans a lineup of NASA Earth-science variables, ranks what is really changing, and shows the evidence: Sen's slope with a 95% confidence interval, a seasonal Mann–Kendall test corrected for testing several variables at once, and a plain-language verdict. When the honest answer is "not proven yet", it says so.

Places come in contrasting pairs, so one variable can be seen trending in opposite directions in different parts of the world. A Time Machine slider shows how a verdict depends on the years you look at.

TerraLens describes what the data shows over the period measured. It makes no forecasts and no claims about causes.

## How it works

```
NASA data (Giovanni / GES DISC)
   -> pipeline/   clean monthly series per place and variable
   -> analysis/   trends, corrected p-values, verdicts, Time Machine windows
   -> backend/    FastAPI (development) and a static JSON export
   -> frontend/   Next.js app that reads the precomputed snapshot
```

Everything the app shows is computed before deployment, so the judged site needs no live server.

| Folder | Purpose |
| -- | -- |
| `pipeline/` | Retrieval and regional aggregation |
| `analysis/` | Statistics |
| `backend/` | API and static export |
| `frontend/` | Web app |
| `geo/regions/` | Place boxes (GeoJSON) |
| `data/` | Processed series, results, sample fixtures (raw files are never committed) |
| `docs/` | Method notes and the AI-use log |

## Getting started

Requirements: [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 for you) and Node 20 or newer.

```bash
uv sync
uv run pytest
uv run uvicorn app.main:app --app-dir backend --reload   # http://localhost:8000/health
```

Frontend (once `frontend/` is scaffolded): `cd frontend && npm install && npm run dev`.

Copy `.env.example` to `.env` for local settings. Never commit credentials. NASA Earthdata credentials go in `~/.netrc` or environment variables.

## Data and attribution

Data comes from NASA via [Giovanni](https://giovanni.gsfc.nasa.gov/) and the NASA GES DISC archive: MERRA-2 monthly reanalysis (NASA Global Modeling and Assimilation Office) and, where used, GPM IMERG. Each processed series has a `provenance.json` recording the product, version, access date and every transformation. MERRA-2 is a model reanalysis constrained by observations, not a direct measurement, and the app labels it that way.

The full reference list is completed from those provenance files before submission.

## AI use

AI tools were used in this project. Every tool, purpose and the files involved are logged in [`docs/ai-use.md`](docs/ai-use.md).

## Licence

MIT. See [`LICENSE`](LICENSE).
