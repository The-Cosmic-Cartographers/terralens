# TerraLens frontend

The TerraLens frontend is a Vite + React application written in JavaScript and JSX. It presents precomputed NASA Earth-system trend results as an evidence-first investigation dashboard for the NASA Space Apps Challenge 2026.

The frontend does not calculate scientific trends. Statistical results, confidence intervals, p-values, verdicts and Time Machine windows are produced upstream by the analysis pipeline and consumed through the API or static JSON export.

## Requirements

- Node.js 20 or newer
- npm
- A modern browser

## Run locally

From this directory:

```bash
npm install
npm run dev
```

Vite serves the application at:

```text
http://localhost:5173
```

Useful validation commands:

```bash
npm run lint
npm run build
npm run preview
```

The project intentionally uses JavaScript/JSX. Do not convert frontend files to TypeScript or introduce Next.js.

## Configuration

Copy `.env.example` to `.env` and choose the data source:

```dotenv
VITE_DATA_MODE=static
VITE_API_BASE_URL=http://localhost:8000
VITE_STATIC_DATA_BASE_URL=/data
```

### Static mode

Static mode is the default and is suitable for the deployed application. The frontend reads JSON files from `public/data/`:

```text
public/data/catalogue.json
public/data/regions.json
public/data/health.json
public/data/metadata/<dataset_id>.json
public/data/lineup/<region_id>.json
public/data/series/<dataset_id>/<region_id>.json
public/data/trend/<dataset_id>/<region_id>.json
public/data/windows/<dataset_id>/<region_id>.json
public/data/compare/<dataset_id>.json
```

For development-only SAMPLE data, set:

```dotenv
VITE_STATIC_DATA_BASE_URL=/data/fixtures
```

SAMPLE data must remain visibly labelled as `SAMPLE DATA — NOT NASA DATA` and must never be presented as a real finding.

### Live API mode

Set:

```dotenv
VITE_DATA_MODE=live
VITE_API_BASE_URL=http://localhost:8000
```

The central client in `src/services/dataClient.js` maps frontend resources to the documented FastAPI routes:

- `GET /health`
- `GET /api/v1/catalogue`
- `GET /api/v1/regions`
- `GET /api/v1/regions/{region_id}/lineup`
- `GET /api/v1/regions/{region_id}/series?dataset_id=`
- `GET /api/v1/regions/{region_id}/trend?dataset_id=`
- `GET /api/v1/regions/{region_id}/windows?dataset_id=`
- `GET /api/v1/compare?dataset_id=`
- `GET /api/v1/metadata?dataset_id=`

The response shapes are defined by the team's Data & API Contracts document. Do not add or rename fields in the frontend to compensate for a backend contract change.

## Application routes

| Route | Purpose |
| --- | --- |
| `/` | Overview, map-based region explorer, investigation start flow and glossary |
| `/explore` | The Lineup: ranked variables for a selected region |
| `/explore/:variableId` | Historical series, evidence record and Time Machine |
| `/compare` | Opposite Trends comparison for one variable across paired regions |
| `/case-files` | Three worked investigations built from supplied results |

## Frontend structure

```text
src/
├── App.jsx                 Application shell, navigation, theme and footer
├── main.jsx                React entry point and route declarations
├── index.css               Global design tokens and base styles
├── App.css                 Dashboard layout and component styles
├── assets/                 Image assets used by the shell
├── components/             Reusable UI and feature components
│   ├── charts/             Recharts chart foundations
│   ├── RegionMap.jsx       MapLibre map and region-box layers
│   ├── RegionExplorer.jsx  Region selection and map/site panel
│   ├── LineupRow.jsx       Ranked result row with sparkline and badges
│   ├── TimeMachine.jsx     Precomputed window selector
│   ├── GlossaryPanel.jsx   Plain-language variable and verdict definitions
│   └── InvestigationStart.jsx  Three-question onboarding flow
├── data/
│   ├── glossary.js         Plain definitions and verdict explanations
│   └── regionOptions.js    Frontend region labels and map framing values
├── hooks/
│   └── useData.js          Loading/error lifecycle for data resources
├── pages/                  Route-level screens
├── services/
│   └── dataClient.js       Central live API/static JSON access layer
└── utils/                  Display and formatting helpers
```

### Data flow

```text
Page or component
    ↓
useData(resource, params)
    ↓
dataClient.js
    ├── live mode → FastAPI
    └── static mode → public/data JSON
    ↓
Loading / error / empty / withheld state
    ↓
Display-only React component
```

React components may format supplied values for display, such as converting a supplied slope from per year to per decade. They must not run Mann–Kendall tests, Sen's slope, confidence-interval calculations, p-value corrections or other scientific analysis.

## Maps and regions

MapLibre GL JS renders the study boxes. Frontend-served GeoJSON is kept in `public/data/regions/`. Source GeoJSON is kept in the repository-level `geo/regions/` directory.

The current frontend region selector contains:

- Ireland
- Iberia
- Sahel / West Africa
- Northwest India
- US Southwest

Dublin and Delhi comparison boxes are also present for the NO₂ comparison track. A GeoJSON box is only a geographic UI asset; it does not mean that a region has a complete scientific result package. The availability of lineup, series, trend and window results is determined by the API/static export.

The map uses the OpenFreeMap style URL configured in `RegionMap.jsx`. Map attribution is enabled through MapLibre. If the map tiles cannot load, the rest of the dashboard should still remain usable.

## Charts

Recharts is the selected chart library. It provides the reusable foundations for:

- Historical line charts
- Supplied trend lines
- Confidence-interval fields when present in the response
- Sparklines
- Comparison cards and supporting visualisations

Charts display values supplied by the analysis output. They do not infer missing scientific values or create replacement statistics.

## UI state rules

The frontend includes shared states for:

- Loading
- API/static request errors
- Empty result sets
- Withheld results
- Coming-soon catalogue entries
- Development SAMPLE data

When a result is unavailable, the UI should explain what is missing rather than showing placeholder numbers as findings.

## Styling

The visual system is implemented with CSS rather than a utility framework:

- Global colours, spacing, typography and chart tokens live in `src/index.css`.
- Dashboard layout, responsive breakpoints and component styling live in `src/App.css`.
- Theme-specific styles are applied through the shell's `theme-dark` and `theme-light` classes.

Keep styles readable and component-focused. Avoid adding a new styling dependency for small UI changes.

## Deployment

Build the static application with:

```bash
npm run build
```

The output is written to `dist/`. `wrangler.jsonc` configures Cloudflare Workers Static Assets and enables SPA fallback routing so React Router routes resolve to `index.html`.

## Ownership and contribution rules

The frontend owner works in:

- `frontend/`
- `geo/`

Do not modify `backend/`, `pipeline/` or `analysis/` for a frontend-only change. If the frontend needs a new endpoint, response field or scientific result, document the requirement and coordinate with the responsible teammate before changing the contract.

AI-assisted development is recorded in [`docs/ai-use.md`](../../docs/ai-use.md).
