# TerraLens package — 2-minute demo

Run from `terralens_repo/` with no network. `pip install -e .` first if the
environment is fresh.

**0:00 — What it is (one sentence).**
"This is the statistics behind the TerraLens app, as a Python package: a region,
a trend, and the uncertainty — without downloading anything."

**0:10 — Regions.**
```python
import terralens as tl

tl.list_regions()
```
"Five POC regions. `tl.ireland` is lazy: nothing is read until I ask for data."

**0:25 — What's inside a region.**
```python
print(tl.ireland.info())
```
"Name, box, area, and which of the five variables have a committed series.
Still no parquet touched."

**0:45 — One summary.**
```python
tl.ireland.summary()
```
"One row per variable: change per decade, 95% interval, p, direction. Sorted by
how large the change is."

**1:05 — One trend.**
```python
trend = tl.ireland.temperature.trend()
trend
trend.plot()
```
"Warming about 0.21 °C per decade since 1981, p below 0.001. The dashed line is
the Sen slope; the points are annual means."

**1:30 — Two places.**
```python
comparison = tl.compare("ireland", "sahel", variables=["temperature"])
print(comparison)
```
"Ireland versus the Sahel. Both intervals are printed. When they overlap, the
text says the ordering is not supported by the intervals — the package will not
pretend two overlapping trends can be ranked."

**1:50 — Why the p can differ from the app.**
"One series is a family of one test, so this p is unadjusted. The app corrects
across its five-row Lineup; every result carries that note in `warnings`, so the
two numbers can disagree without either being wrong."

**2:00 — Close.**
"Same data, same test, same caveats — in three lines."

## Appendix — the full 5 × 5 (not spoken)

Change per decade from each region's committed series. Units differ by column,
so compare down a column, never across rows.

| region | temperature (°C) | soil moisture (m³/m³) | evapotranspiration (mm/day) | precipitation (mm annual total) | aerosol (AOD) |
| --- | --- | --- | --- | --- | --- |
| iberia | +0.25* | +0.0003 | +0.02 | +5.31 | -0.009* |
| ireland | +0.21* | +0.0010 | +0.02* | +18.21 | -0.010* |
| nw_south_asia | -0.02 | +0.0100* | +0.11* | +66.32* | +0.043* |
| sahel | +0.17* | +0.0022 | +0.04 | +20.66 | -0.011* |
| us_southwest | +0.46* | -0.0057* | -0.05* | -23.23* | -0.007* |

`*` marks p < 0.05 for that single series. These p-values are unadjusted
(family size 1); the app's Lineup applies Benjamini–Hochberg, so a starred row
here can be unstarred there. Columns are ordered as in `summary()`.
