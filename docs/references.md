# References

<!-- Generated from data/processed/*/provenance.json and pyproject.toml by `uv run python -m pipeline.references` — do not edit by hand. -->

## Data

- NASA GES DISC Giovanni, *MERRA-2 2 m air temperature*, M2TMNXSLV v5.12.4, Ireland (-10.5,51.4,-6.0,55.4), 1981-01–2025-12, accessed 2026-11-14. https://giovanni.gsfc.nasa.gov/giovanni/#service=ArAvTs&starttime=1981-01-01T00:00:00Z&endtime=2025-12-31T23:59:59Z&bbox=-10.5,51.4,-6,55.4&data=M2TMNXSLV_5_12_4_T2M
- NASA GES DISC Giovanni, *MERRA-2 2 m air temperature*, M2TMNXSLV v5.12.4, Sahel (0.0,12.0,20.0,18.0), 1981-01–2025-12, accessed 2026-11-14. https://giovanni.gsfc.nasa.gov/giovanni/#service=ArAvTs&starttime=1981-01-01T00:00:00Z&endtime=2025-12-31T23:59:59Z&bbox=0,12,20,18&data=M2TMNXSLV_5_12_4_T2M
- NASA GES DISC Giovanni, *MERRA-2 2 m air temperature*, M2TMNXSLV v5.12.4, US Southwest (-115.0,31.0,-105.0,38.0), 1981-01–2025-12, accessed 2026-11-14. https://giovanni.gsfc.nasa.gov/giovanni/#service=ArAvTs&starttime=1981-01-01T00:00:00Z&endtime=2025-12-31T23:59:59Z&bbox=-115,31,-105,38&data=M2TMNXSLV_5_12_4_T2M

## Software

- `fastapi>=0.115`
- `uvicorn>=0.30`
- `pydantic>=2.8`
- `pandas>=2.2`
- `numpy>=1.26`
- `pyarrow>=16`
- `xarray>=2024.6`
- `scipy>=1.13`
- `statsmodels>=0.14`
- `pymannkendall>=1.4.3`
- `geopandas>=1.0`
- `shapely>=2.0`
- `matplotlib>=3.8`
- `pytest>=8` (development)
- `httpx>=0.27` (development)
- `ruff>=0.6` (development)

## Methods

- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*, 13(3), 245–259. — the Mann–Kendall trend test.
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau. *Journal of the American Statistical Association*, 63(324), 1379–1389. — Sen's slope.
- Hamed, K. H., & Rao, A. R. (1998). A modified Mann–Kendall trend test for autocorrelated data. *Journal of Hydrology*, 204, 182–196. — the Hamed–Rao variance correction used on monthly series.

## Not used, therefore not cited

- **KNMI Climate Explorer** — not cited: no cross-check was run; that stretch row was never started.
- **SeaWiFS** — not cited: no ocean-colour variable is in the Lineup.
- **AppEEARS** — not cited: the NDVI stretch row was never started.
- **NOAA CDO** — not cited: no station data was pulled — the token never arrived.
- **NASA POWER** — not cited: used once as a cross-check for T2M, then superseded by the Giovanni export; the committed series do not come from it.
