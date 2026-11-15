# TerraLens (Python package)

TerraLens is a small, offline Python library for one question: is this NASA
Earth-science variable actually changing in this place, and how much can the
record support?

Five regions and five variables ship with the package. A trend is one call:
Sen's slope per decade, a 95% confidence interval, a seasonal Mann–Kendall test
that accounts for serial correlation, a plain-language verdict, and the caveats
that qualify it. Compare two regions on matching periods, or read all five
variables for one place at once.

All the data is in one place: the five regions, 25 monthly series and their
provenance ship inside the wheel, ready to analyse offline. The core statistics
are the same ones behind the TerraLens app. The package is standalone — no UI
code, no frontend dependency.

## Install

The package is currently published on **TestPyPI**, not real PyPI. Install the
verified test release with:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ terralens-earth==0.1.2
```

`--extra-index-url` is required because TestPyPI hosts only `terralens-earth`;
pandas, numpy, pyarrow, scipy and matplotlib come from PyPI.

Once the first real PyPI release is published, the command becomes simply
`pip install terralens-earth`.

The distribution is `terralens-earth`; the import name is `terralens`. The
wheel bundles the five regions, the 25 monthly series and their provenance, so
importing and analysing work from one installed snapshot.

To work on the package from a checkout:

```bash
cd terralens_repo
pip install -e .
python -m pytest terralens/tests -q
```

No network is used at import or analysis time.

## 30-second quickstart

```python
import terralens as tl

tl.list_regions()  # ['iberia', 'ireland', 'nw_south_asia', 'sahel', 'us_southwest']

ie = tl.ireland
print(ie.info())  # box, area, and which variables are available

ie.summary()  # one row per variable: per-decade change, p, direction
trend = ie.temperature.trend()
trend  # Air temperature (2 m): Warming +0.21 °C/decade, p<0.001, 1981-2025
trend.to_csv()  # or .to_dict(), .to_json(), .plot()

tl.compare("ireland", "sahel", variables=["temperature"]).table
```

## Before / after

Before — the loop every project rewrites (download a product, subset a box,
convert units, build a monthly series, check coverage, run a trend test, keep
the metadata straight):

```python
# some variant of this, per variable, per region, per project
subset = open_dataset(url).sel(lat=slice(south, north), lon=slice(west, east))
monthly = subset.resample(time="1MS").mean()
monthly.to_dataframe().to_csv(...)
# then find a Mann-Kendall implementation and hope it matches last time
```

After:

```python
import terralens as tl

tl.ireland.temperature.trend()
```

Same series, same seasonal Mann–Kendall with the Hamed–Rao correction and the
same Sen slope, plus the citation and the caveats attached to the result.

## API

| call | returns |
| --- | --- |
| `tl.list_regions()` | region ids |
| `tl.region("ireland")`, `tl.ireland` | `Region` |
| `region.info()` | readable summary; reads no data |
| `region.summary()` | `DataFrame`, one row per available variable |
| `region.temperature` (and `.soil_moisture`, `.evapotranspiration`, `.precipitation`, `.aerosol`) | `Variable` |
| `variable.load()` | `DataFrame` with `date`, `value`, `coverage_fraction` |
| `variable.trend()` | `TrendResult` |
| `variable.anomalies(baseline=(1991, 2020))` | `DataFrame` with `anomaly` |
| `variable.seasonal()` | `DataFrame`, mean anomaly by calendar month |
| `variable.plot()` | matplotlib axes |
| `tl.compare(a, b, variables=None)` | `Comparison` with `.table`, `.ranking`, `.plot()`, `str()` |
| `tl.adjust_bh(results)` | list of `TrendResult` with BH q-values and recomputed verdicts |

`Region.cells(variable_id)` estimates native grid cells inside the box and warns
when a region is too small to be treated as a regional average.

## Multiple testing

`trend()` reports one test, so its p-value is unadjusted. When several results
answer one question, pass them together and let the package apply
Benjamini–Hochberg across that family:

```python
ie = tl.ireland
results = [
    ie.temperature.trend(),
    ie.soil_moisture.trend(),
    ie.evapotranspiration.trend(),
    ie.precipitation.trend(),
    ie.aerosol.trend(),
]
adjusted = tl.adjust_bh(results)

adjusted[0].p_value  # raw p
adjusted[0].adjusted_p_value  # BH q-value
adjusted[0].family_size  # 5
adjusted[0].verdict  # recomputed from q
```

The caller defines the family. `adjust_bh` preserves input order and leaves
withheld results in the list with `adjusted_p_value=None`; they are not counted
as tests. The app uses two families: the five variables within a region's
Lineup, and one variable across regions for compare.

## Data sources and attribution

All series are NASA products, bundled with the installed package (and mirrored
under `data/processed/` in the repository) with provenance built by the
project's pull pipeline.

| variable | product | version | window |
| --- | --- | --- | --- |
| 2 m air temperature | MERRA-2 M2TMNXSLV | 5.12.4 | 1981–2025 |
| soil moisture 0–5 cm | MERRA-2 M2TMNXLND (SFMC) | 5.12.4 | 1980–2025 |
| evapotranspiration | MERRA-2 M2TMNXLND (EVLAND) | 5.12.4 | 1980–2025 |
| precipitation (bias-corrected model output) | MERRA-2 M2TMNXFLX (PRECTOTCORR) | 5.12.4 | 1980–2025 |
| aerosol optical thickness | MERRA-2 M2TMNXAER | 5.12.4 | 1980–2025 |

Access routes (Giovanni area averaging or Harmony subsetting) are recorded per
series in the processed data; `TrendResult.citation` names the product and
version that produced the number.

## Limitations

- **Box averages.** A region is a latitude/longitude box, so it takes in ocean
  and neighbouring land by construction. Area-weighted zonal statistics and
  polygons are roadmap items.
- **Resolution.** A dataset's native grid is coarser than some boxes; the
  package warns when a box covers fewer than about four cells.
- **Unadjusted single-series p.** One series is a family of one test, so its
  p-value is unadjusted. The app applies Benjamini–Hochberg across its Lineup
  and compare families, so an app verdict can be more conservative. Use
  `tl.adjust_bh(results)` to adjust an explicit family; every unadjusted
  `TrendResult` carries this caveat in `warnings`.
- **Model output, not measurements.** Every series is MERRA-2 reanalysis, the same
  record as the app. Soil moisture is the 0–5 cm layer, precipitation is
  bias-corrected model output (not the IMERG satellite estimate), and the land
  fields are not weighted by land fraction.
- **No causation.** The package reports association over time, not causes.
- **POC coverage.** Five regions and five variables ship here; further variables
  are one subclass each.

## Tests

```bash
python -m pytest terralens/tests -q
```

The contract test pins the Ireland temperature trend to the committed Lineup
result to 1e-12, so the package cannot silently drift from the app.

## Adding a region or a variable

- A region is one entry in `terralens/_data/regions.json` (west, south, east,
  north); it appears in `tl.list_regions()` automatically once its series exist.
- A variable is one small subclass in `terralens/variables/`, with its dataset
  id and alias registered in `variables/__init__.py`. Statistics are inherited.
