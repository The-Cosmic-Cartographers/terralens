# pipeline/

**Owner: Parth.** Retrieval and regional aggregation: raw NASA series (Giovanni area-averaged CSV, or GES DISC subsets) become one clean monthly series per place and variable.

- Writes `data/processed/<dataset_id>/<region_id>.parquet` and `provenance.json` next to it (schema in Linear doc 04).
- Raw downloads go in `data/raw/` and are never committed.
- Every series carries units, coverage and the product/version it came from. Convert units here (K to °C, kg m-2 s-1 to mm/day) and cut every series at 2025-12-31.
- Giovanni snaps boxes to the grid and reports an "analyzable region": record it in `provenance.json`.
- Tests go next to the code as `test_*.py`.

## One command: `pipeline.pull` (NAS-60)

```bash
export EARTHDATA_TOKEN=...                      # never written to disk, logs or provenance
uv run python -m pipeline.pull --all              # every series, then build
uv run python -m pipeline.pull --variable-id aerosol --region-id ireland
uv run python -m pipeline.pull --all --dry-run    # print the plan, no token needed
```

It plans per variable, pulls what a route can serve, writes `data/raw/<variable>_<region>.csv`, then calls `pipeline.build` so `data/processed/` is ready without a second command.

### Routes, and why they are not interchangeable

| Variable | Route | Products |
| -- | -- | -- |
| T2M | **Giovanni only** (kept) | the committed series is a Giovanni export; Harmony can subset `M2TMNXSLV` but would overwrite the same raw file, so the pull refuses this row and says so |
| aerosol | Harmony | MERRA-2 `M2TMNXAER` (`C1276812866-GES_DISC`), field `TOTEXTTAU` |
| soil moisture 0–10 | Harmony | GLDAS-2.1 `GLDAS_NOAH025_M` (`C1342986036-GES_DISC`), field `SoilMoi0_10cm_inst` |
| evapotranspiration | Harmony | same GLDAS collection, field `Evap_tavg` |
| precipitation | **Giovanni only** | Harmony registers no coverage for `GPM_3IMERGM`; export the CSV in ≤13-year windows |
| NO₂ | **no verified route** | `OMNO2d` exists in CMR but no field name has been proven from this pipeline |

A blocked series is reported by name and exit code, never filled with a substitute or a different
product. `--dry-run` shows which is which before anything runs.

### The footprint rule

Harmony returns every cell that **intersects** the requested box, while Giovanni analyses only cells
whose **centre** lies inside it. Averaging the intersecting set pulls a regional mean towards the
surrounding climate — on T2M Ireland that was 0.88 °C at worst. `month_means` therefore masks to
centre-in-box before averaging, and `slice_extent` records the extent of the cells that were
actually averaged in `provenance.json` (`analyzable_region`), which is usually one cell narrower
than the requested box on each side. With the mask, a Harmony pull reproduces the Giovanni T2M
series to 0.0005 °C (RMS 0.0003 °C).

### What makes it survive this network

- **Keep-alive sessions per worker** (`--workers`, default 8). The host resets roughly one TLS handshake in three; reusing connections, not more retries, is what makes a run finish.
- **Checkpoints** in `data/raw/.pull/<dataset>_<region>.json`, written after every chunk. A killed run resumes; `pull` never re-submits a chunk whose months are already stored.
- **Capped retries**: `--attempts` per slice, then `--rounds` extra passes over the missing months only.
- **Total budget**: `--time-limit` seconds (default 1800). On expiry the run stops at a chunk boundary and exits `3`; rerunning resumes.
- **Exit codes**: `0` complete, `2` missing credentials/config, `3` time limit, `4` at least one series failed or is blocked.

### When NASA's service is down

Harmony jobs that end `failed`/`canceled` are retried in a later round; if the whole service is out,
the run stops with the job status in the message and the checkpoint keeps every month already
parsed. Rerun the same command later — nothing is re-downloaded. For IMERG, use the Giovanni
windowed route (13 years per request) and drop the CSV in `data/raw/` as
`precipitation_<region>.csv`; `pipeline.build` reads both routes identically.

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

At ~2 min per series, the 22 Harmony slices in the plan — soil moisture, evapotranspiration and
aerosol over five regions — come to roughly **45 minutes**, which is over the 30-minute target.
That is why resuming is the default design rather than an extra: `--time-limit 1800` stops at a
chunk boundary and the next run continues from the checkpoints. T2M is not in that count (it stays
on Giovanni), and precipitation and NO₂ are refused rather than pulled.

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
