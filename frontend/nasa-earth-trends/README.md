# TerraLens frontend

TerraLens is a Vite + React + JavaScript frontend for investigating precomputed Earth-system trends.

## Development

```bash
npm install
npm run dev
npm run lint
npm run build
```

## Data modes

The central client in `src/services/dataClient.js` supports `VITE_DATA_MODE=live` for the FastAPI service and `VITE_DATA_MODE=static` for a deployed JSON snapshot. The API paths currently implemented are catalogue, regions and metadata. Set `VITE_API_BASE_URL` and `VITE_STATIC_DATA_BASE_URL` in `.env` as needed.

The repository does not yet expose the static snapshot under the frontend's public directory, and result routes for lineup, variable trends, comparison and case files are not implemented in the backend. Until those integrations land, the UI shows explicit loading, empty, error or not-connected states and never invents scientific findings.

## Chart decision

Recharts is the selected chart library for D11. Its responsive line-chart primitives provide the foundation for historical series, trend lines, confidence intervals, sparklines and comparison views while keeping scientific calculations in the analysis pipeline.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
