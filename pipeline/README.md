# pipeline/

**Owner: Parth.** Retrieval and regional aggregation: NASA GES DISC subsets become one clean monthly series per place and variable.

- Writes `data/processed/<dataset_id>/<region_id>.parquet` and `provenance.json` next to it (schema in Linear doc 04).
- Raw downloads go in `data/raw/` and are never committed.
- Every series carries units, coverage and the product/version it came from. Convert units here (K to °C, kg m-2 s-1 to mm/day) and cut every series at 2025-12-31.
- Harmony subsets the requested box; the pipeline applies the centre-in-box footprint and records the cells averaged in `provenance.json`.
- Tests go next to the code as `test_*.py`.

## One command: `pipeline.pull` (NAS-60)

```bash
export EARTHDATA_TOKEN=...                      # never written to disk, logs or provenance
uv run python -m pipeline.pull --all              # every series, then build
uv run python -m pipeline.pull --all --env-file .env  # local KEY=VALUE credentials
uv run python -m pipeline.pull --variable-id aerosol --region-id ireland
uv run python -m pipeline.pull --all --dry-run    # print the plan, no token needed
```

It plans per variable, pulls what a route can serve, writes `data/raw/<variable>_<region>_<route>.csv`, then calls `pipeline.build` so `data/processed/` is ready without a second command. Harmony files use the `harmony` suffix, preserving any older Giovanni export. Credentials may be named `EARTHDATA_TOKEN` or `EARTH_DATA_API`; values from the process environment take precedence over the optional env file.

### Routes, and why they are not interchangeable

| Variable | Route | Products |
| -- | -- | -- |
| T2M | Harmony | MERRA-2 `M2TMNXSLV` (`C1276812859-GES_DISC`), field `T2M` |
| aerosol | Harmony | MERRA-2 `M2TMNXAER` (`C1276812866-GES_DISC`), field `TOTEXTTAU` |
| soil moisture 0–5 | Harmony | MERRA-2 `M2TMNXLND` (`C1276812856-GES_DISC`), field `SFMC` (volumetric, m³/m³) |
| evapotranspiration | Harmony | same land collection, field `EVLAND` (kg m⁻² s⁻¹, stored as mm/day) |
| precipitation | Harmony | MERRA-2 `M2TMNXFLX` (`C1276812868-GES_DISC`), field `PRECTOTCORR` (bias-corrected, kg m⁻² s⁻¹, stored as mm/month) |
| NO₂ | **OPeNDAP daily granule subset** | `OMNO2d` V004 (`C3333493715-GES_DISC`), field `ColumnAmountNO2TropCloudScreened`, one subset per city per day from `pipeline.no2` |

A blocked series is reported by name and exit code, never filled with a substitute or a different
product. `--dry-run` shows which is which before anything runs.

### Why the long record is MERRA-2 throughout

All five MVP rows use MERRA-2 through Harmony. Soil moisture, evapotranspiration, precipitation and aerosol cover 1980–2025; the verified air-temperature record covers 1981–2025 (45 calendar years). The older series are retained in `data/archive/`. The cost: soil moisture is the 0–5 cm layer, precipitation and land evaporation are model output, and the land fields are not weighted by land fraction (`FRLAND`).

### The footprint rule

Harmony returns every cell that **intersects** the requested box. `month_means` masks to cells
whose **centre** lies inside it before averaging, and `slice_extent` records the extent of the
cells actually averaged in `provenance.json` (`analyzable_region`). On the prior T2M comparison,
this footprint reproduced the Giovanni series to 0.0005 °C (RMS 0.0003 °C).

### The NO₂ route

OMNO2d is a *daily* product: one cloud-screened retrieval per day, absent where the sky was not
clear. It therefore cannot be a monthly subset, and the other routes do not serve V004 at all —
Harmony rejects the variable name (`Coverages were not found`), Giovanni's time-series API knows the
product only as V003, its Simple Subset Wizard answers `dataSetNotConfigured`, the S3 direct-access
role is not authorised on the protected bucket, and no-auth/HTTP-Basic both bounce to Earthdata Login.

`pipeline.no2` uses the granule-level OPeNDAP service instead: one request per city per day returns
the box's cells as a NetCDF subset, 1–3 kB against the 11 MB global granule, with no redirect hop.
The daily values go through `pipeline.omi`, so a month needs **10 clear days** and carries its
`n_valid_days`; below that the month is kept as a null row with its count. The 34 days of known Aura
outages in 2005–2025 have no granule at all and are reported as gaps, never as failed downloads.

### What makes it survive this network

- **Keep-alive sessions per worker** (`--workers`, default 8). The host resets roughly one TLS handshake in three; reusing connections, not more retries, is what makes a run finish.
- **Checkpoints** in `data/raw/.pull/<dataset>_<region>.json`, written after every chunk. A killed run resumes; `pull` never re-submits a chunk whose months are already stored.
- **Capped retries**: `--attempts` per slice, then `--rounds` extra passes over the missing months only.
- **Total budget**: `--time-limit` seconds (default 1800). On expiry the run stops at a chunk boundary and exits `3`; rerunning resumes.
- **Exit codes**: `0` complete, `2` missing credentials/config, `3` time limit, `4` at least one series failed or is blocked.

### When NASA's service is down

Harmony jobs that end `failed`/`canceled` are retried in a later round; if the whole service is out,
the run stops with the job status in the message and the checkpoint keeps every month already
parsed. Rerun the same command later — nothing is re-downloaded. The five MVP rows stay on their
registered MERRA-2 products; the puller reports failures instead of substituting IMERG or another
dataset.

### Measured (2026-11-14, this machine, home connection)

| Step | Time | Note |
| -- | -- | -- |
| Harmony job, 5-year chunk | ~90 s | job poll waits 5 s per status call; the subset itself is seconds |
| Slices per chunk | 60 | one netCDF per month, ~2–4 MB each |
| Download pass, 60 slices, 8 workers | ~20–40 s | keep-alive sessions; without them roughly one handshake in three was reset |
| Parse + area mean, 60 slices | ~5 s | cosine-latitude weighted mean in a thread pool |

A 26-year series is five chunks, so roughly 2 min per series when GES DISC is answering. The
slowest step is the job poll, not the download.

### Dependencies, and the real total

New runtime dependencies: `requests` (the keep-alive sessions), `harmony-py` (job submission)
and `netcdf4` (the engine behind `xarray`, which was already a dependency). No browser, no
Selenium, nothing installed at run time.

At ~2 min per series, the 25 Harmony slices in the plan — all five MVP rows over five regions —
come to roughly **50 minutes**, which is over the 30-minute target.
That is why resuming is the default design rather than an extra: `--time-limit 1800` stops at a
chunk boundary and the next run continues from the checkpoints. NO₂ is not in that count; its daily
OPeNDAP route is separate.

NO₂ is additive to that budget: 15,272 city-days over 2005–2025 at roughly 15 subsets per second
is about 17 minutes for both cities, and its checkpoint is per day, so `--time-limit` stops it just
as cleanly.

**Today's block, and why the command still behaved:** every GES DISC read returned
`403 EULA Acceptance Failure` (`data.gesdisc.earthdata.nasa.gov`), which is also what broke
Harmony's OPeNDAP subsetter — jobs died at 23% with `Subsetter failed with error: 403`. The
pull exited `4`, named the job and the series, and left the checkpoint empty; nothing was
substituted.

That EULA has since been accepted (`nasa_gesdisc_data_archive` appears under approved
applications), and jobs still die the same way, now on OPeNDAP's side of the chain: the
subsetter cannot read the granule's DMR++
(`Failed to read the DMR++ from S3 … 403`), which is a service credential, not ours. Metadata
alone (`…​.dmr.xml`) returns 200, so the collection and our token are fine. Until OPeNDAP
serves those granule sidecars again, Harmony and direct OPeNDAP `.dods` both fail; the pull
reports it per series and the rerun resumes.

## Checking the processed data (NAS-41)

`python -m pipeline.qa` reads every folder in `data/processed/` and checks it against
`pipeline/registry.py` and its own `provenance.json`:

- contract columns, with anything outside the contract reported as a warning;
- the unit stored in the file equals the registry's output unit, and the provenance
  `output_unit` and `version` agree with the registry;
- every month of the registered window is present exactly once;
- the provenance period matches the file, and `requested_box` parses as W,S,E,N inside
  valid coordinates (a box that differs from `pipeline/regions.json` is a warning);
- the sha256 of the export the series was built from matches the hash in provenance. A file
  with the recorded name but different bytes is an error (it is a different pull); an export
  that is simply absent is a warning, because `data/raw` is not committed and the recorded
  export may live elsewhere. A provenance with no hash at all is an error;
- provenance regions and parquet files are one-to-one, and an empty permalink is only a
  warning (the two Ireland GLDAS pulls never logged a job id).

`python -m pipeline.qa --regenerate` additionally rebuilds each series from its raw CSV into
a temporary directory and compares values and timestamps row by row.

Exit codes: `0` clean (warnings allowed), `1` errors found, `2` errors found while
regenerating.
