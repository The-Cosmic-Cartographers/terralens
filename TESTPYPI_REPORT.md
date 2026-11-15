# TestPyPI report — `terralens-earth` 0.1.2

Date: 2026-11-15
Status: **published to TestPyPI and verified by installing from the index.**

Project: https://test.pypi.org/project/terralens-earth/0.1.2/

`0.1.0` and `0.1.1` remain on TestPyPI for history; `0.1.2` supersedes them.
Real PyPI was not touched.

## Published artifacts

| File | Size | SHA-256 |
| -- | -- | -- |
| `terralens_earth-0.1.2-py3-none-any.whl` | 203,122 B | `8f413268a8cd19b9353f8a8743bf431b3d25bfa8510f71c1002d8a7a87b1b1aa` |
| `terralens_earth-0.1.2.tar.gz` | 118,478 B | `8171baf8523e757d019986b9b20867934b53ac385c42dfab7803435070a2f25b` |

The TestPyPI JSON API and simple index return the same filenames, sizes and
hashes.

## What changed in 0.1.2

- README install command is now one line:
  `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ terralens-earth==0.1.2`
- Install pin updated to `0.1.2`.
- No code changes from 0.1.1.

`0.1.1` introduced public `tl.adjust_bh(results)`, BH q-values on
`TrendResult`, the rewritten README description, and the TestPyPI install
section.

## Verification before upload

| Check | Result |
| -- | -- |
| Clean build | PASS — wheel + sdist |
| `twine check dist/*` | PASS — both artifacts |
| Full repository suite | PASS — 328 passed |
| Package suite | PASS — 41 passed |
| Wheel layout | PASS — only `terralens` + dist-info |
| Bundled data | PASS — 25 parquet files, `_data/regions.json` |
| Metadata install line | PASS — single line, `0.1.2` pin |

## Verification from TestPyPI

```bash
/tmp/tl-testpypi-012/Scripts/python.exe -m pip install -q --no-cache-dir --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ terralens-earth==0.1.2
```

Result: `Successfully installed terralens-earth-0.1.2`; `pip check` reports no
broken requirements.

Installed-package checks, run from `C:\Users\nandi\AppData\Local\Temp`:

- `terralens.__version__` → `0.1.2`
- package README metadata contains the single-line install command with the
  `0.1.2` pin
- `tl.adjust_bh` over Ireland's five variables → family size 5
  - t2m: q `7.6e-05`
  - soil moisture: q `0.1231`, verdict `no_clear_trend`
- `compare()` returns `Comparison`

## Install command

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ terralens-earth==0.1.2
```

`--extra-index-url` is required because TestPyPI does not host pandas, numpy,
pyarrow, scipy or matplotlib.

## Known limitations

- Only Python 3.11 was exercised end to end; classifiers claim 3.11–3.13.
- Dependency floors (`pandas>=2.2`, `numpy>=1.26`) were not tested; the clean
  install used current releases.
- TestPyPI is a sandbox: projects and releases may be deleted, so this URL is
  not a permanent distribution channel.
- Nothing has been published to real PyPI.
