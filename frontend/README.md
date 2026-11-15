# TerraLens frontend workspace

This directory contains the frontend implementation for TerraLens, the NASA Space Apps Challenge 2026 Earth-system trend investigation dashboard.

**Owner: Bhargav.**



The frontend/GIS work is maintained in:

- `frontend/` — web application code and static frontend assets
- `geo/` — source geographic data and GeoJSON region boxes

Do not modify `backend/`, `pipeline/` or `analysis/` for a frontend-only task. If the frontend needs a new endpoint, response field, dataset or scientific result, coordinate with the responsible teammate before changing a contract.

## Application

The active Vite + React application is located at:

```text
frontend/nasa-earth-trends/
```

Read the application guide for setup, routes, data modes, maps, charts and deployment:

- [`frontend/nasa-earth-trends/README.md`](nasa-earth-trends/README.md)

## Quick start

```bash
cd frontend/nasa-earth-trends
npm install
npm run dev
```

The development server runs at [http://localhost:5173](http://localhost:5173).

Validation commands:

```bash
npm run lint
npm run build
```

## Technology

- Vite
- React
- JavaScript and JSX
- React Router
- MapLibre GL JS
- Recharts
- CSS design tokens and responsive dashboard styles

## Data boundary

The frontend consumes precomputed results through either:

1. Kevin's FastAPI service in live mode.
2. Static JSON files in `frontend/nasa-earth-trends/public/data/`.

The browser displays supplied values and metadata. It does not calculate trends, confidence intervals, p-values, statistical corrections or Time Machine windows.

## AI-assisted development

AI-assisted work is recorded in [`docs/ai-use.md`](../docs/ai-use.md).
