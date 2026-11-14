# TerraLens

**Other tools chart the trend you already suspected. TerraLens finds the suspects.**

TerraLens is an Earth-system trend discovery tool built for the NASA Space Apps Challenge 2026, *Be An Earth System Trend Detective!*. Pick a place and it scans a lineup of five NASA Earth-science variables, ranks what is really changing, and shows the evidence: Sen's slope with a 95% confidence interval, a seasonal Mann–Kendall test corrected for testing several variables at once, and a plain-language verdict. When the honest answer is "not proven yet", it says so.

Places come in contrasting pairs, so one variable can be seen trending in opposite directions in different parts of the world. A Time Machine slider shows how a verdict depends on the years you look at.

TerraLens describes what the data shows over the period measured. It makes no forecasts and no claims about causes.

> **Status:** under development during the hackathon (14–15 Nov 2026). Real MERRA-2 air temperature for Ireland, Sahel and US Southwest is processed, tested and served as a static snapshot. The other four variables and the finished web pages are still landing, so every verdict is provisional.
>
> **Live (hosting preview):** https://terralens.kevin-henry-333.workers.dev

## What you can do with it

| Pillar | Question | What you see |
| -- | -- | -- |
| **The Lineup** | What is changing here? | One ranked board per place: five variables, each with a sparkline, slope per decade, a verdict and a badge saying whether it is a satellite estimate, a land model or a reanalysis |
| **Opposite Trends** | Where, and which way? | One variable side by side across places, on matching periods |
| **The Time Machine** | Is it significant, and would it be? | Drag the start and end year and see the slope, confidence interval and verdict change. For trends that are not significant, an estimate of how many years of record it would take to detect one that size |

## Places and variables

Five regions, chosen in contrasting pairs, plus two city boxes for air quality:

Ireland · Iberia · Sahel (West Africa) · NW South Asia (Thar–Indus) · US Southwest (Colorado Basin) · Dublin and Delhi NCR (NO₂ only)

Each region is scanned for these variables, all through NASA Giovanni:

| Variable | Product | Type |
| -- | -- | -- |
| Air temperature (2 m) | MERRA-2 M2TMNXSLV v5.12.4 | Model reanalysis |
| Soil moisture (0–10 cm) | GLDAS-2.1 GLDAS_NOAH025_M | Land model |
| Evapotranspiration | GLDAS-2.1 GLDAS_NOAH025_M | Land model |
| Precipitation | GPM IMERG Final monthly v07 | Satellite estimate |
| Aerosol optical depth | MERRA-2 M2TMNXAER v5.12.4 | Model reanalysis |
| NO₂ column (Dublin, Delhi only) | OMI OMNO2d v004, 30% cloud screened | Satellite |

Each variable is analysed over whole calendar years ending at the last complete year, and every row shows its own period.

## The method in plain words

1. **Monthly series.** Each variable is averaged over the place's box, one value per month.
2. **Remove the seasons.** We subtract each calendar month's normal value, so summer-versus-winter swings do not look like a trend.
3. **Is there a trend?** A seasonal Mann–Kendall test asks whether the values tend to rise or fall over the years, without assuming the data follow a bell curve. We allow for the fact that neighbouring months are not independent.
4. **How big?** Sen's slope is the typical change per year (shown per decade), with a 95% confidence interval. We also show the size as "about k times the normal year-to-year swing", so a statistically clear but tiny change is not mistaken for a big one.
5. **Testing five things at once finds coincidences.** Scan five variables and one will look significant by chance more often than you would expect. We correct for that with Benjamini–Hochberg and base every verdict on the corrected p-value. The raw one is shown too.
6. **Verdicts.** Significant trend (corrected p < 0.05), Weak evidence (0.05 to 0.10), No clear trend (0.10 or more), Not enough data (too few years or too many missing months; the result is withheld, not hidden).
7. **Time Machine.** The same test is run for every window of at least ten whole years, so the slider only reads precomputed results.
8. **Would more years help?** For a trend that is not significant, we estimate how many years of record a trend of that size would need to be detected (Weatherhead et al., 1998). This is a statement about evidence, not a forecast.

Limits worth knowing: MERRA-2 is a model reconstruction constrained by observations, so changes in what it assimilates can create artificial steps, aerosol most of all. Satellite rows (IMERG, OMI) are shown beside model rows for that reason. A box average hides what happens inside the box. Statistics cannot say why a trend happened, and the app does not try.

## How it works

```
NASA data (Giovanni / GES DISC)
   -> pipeline/   clean monthly series per place and variable
   -> analysis/   trends, corrected p-values, verdicts, Time Machine windows
   -> backend/    FastAPI (development) and a static JSON export
   -> frontend/   Vite + React app that reads the precomputed snapshot
```

Everything the app shows is computed before deployment, so the judged site needs no live server. The backend only reads files and never computes statistics.

| Folder | Purpose |
| -- | -- |
| `pipeline/` | Retrieval and regional aggregation |
| `analysis/` | Statistics |
| `backend/` | API and static export |
| `frontend/nasa-earth-trends/` | Web app (Vite + React) |
| `geo/regions/` | Place boxes (GeoJSON) |
| `data/` | Processed series, results, SAMPLE fixtures (raw files are never committed) |
| `docs/` | The AI-use log |

## Getting started

Requirements: [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 for you) and Node 20 or newer.

```bash
uv sync
uv run pytest
```

Run the API against the SAMPLE fixtures (made-up numbers, clearly marked, for development only):

```bash
TERRALENS_DATA_DIR=./data/fixtures uv run uvicorn app.main:app --app-dir backend --reload
```

Then open http://localhost:8000/health or http://localhost:8000/docs.

Write the static JSON snapshot the web app reads:

```bash
# real data (refuses data marked SAMPLE)
PYTHONPATH=backend uv run python -m app.export

# development with the fixtures
PYTHONPATH=backend uv run python -m app.export --data-dir data/fixtures --allow-sample
```

Frontend: `cd frontend/nasa-earth-trends && npm install && npm run dev` (Vite serves http://localhost:5173). To develop against the SAMPLE data, write the snapshot where its `.env.example` expects it: `PYTHONPATH=backend uv run python -m app.export --data-dir data/fixtures --out frontend/nasa-earth-trends/public/data/fixtures --allow-sample`.

Copy `.env.example` to `.env` for local settings. Never commit credentials. NASA Earthdata credentials go in `~/.netrc` or environment variables. More detail is in [`backend/README.md`](backend/README.md) and [`data/README.md`](data/README.md).

## Data and attribution

All data comes from NASA through [Giovanni](https://giovanni.gsfc.nasa.gov/), part of the NASA GES DISC archive:

- MERRA-2 monthly reanalysis, v5.12.4 (NASA Global Modeling and Assimilation Office)
- GLDAS-2.1 Noah land surface model, 0.25° monthly (NASA GSFC)
- GPM IMERG Final Run monthly, v07 (NASA)
- OMI OMNO2d NO₂ tropospheric column, v004 (NASA, Aura OMI)

Each processed series has a `provenance.json` recording the product, version, region box, Giovanni's analysed region, access date and every transformation. The full reference list, with citations and access dates, is completed from those files before submission.

Method references: Weatherhead et al. (1998), *Factors affecting the detection of trends: statistical considerations and applications to environmental data*, J. Geophys. Res. 103(D14); Wilks (2016), Bull. Amer. Meteor. Soc. (false-discovery-rate control, for the optional trend map); the NASA SeaWiFS chlorophyll time-series paper listed among the challenge resources.

## AI use

AI tools were used in this project. Every tool, purpose and the files involved are logged in [`docs/ai-use.md`](docs/ai-use.md). We have not used AI to choose which variables are trending: the statistics do that.

## Licence

MIT. See [`LICENSE`](LICENSE).
