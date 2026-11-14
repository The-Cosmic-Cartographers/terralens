# data/

| Folder | Contents | Committed? |
| -- | -- | -- |
| `raw/` | Files exactly as downloaded from NASA | **Never** (gitignored) |
| `processed/<dataset_id>/` | Clean monthly series (Parquet) and `provenance.json` | Yes (small files only) |
| `results/` | `trends.json`, lineup and Time Machine window files | Yes |
| `fixtures/` | SAMPLE data for development, in the same schemas | Yes |

**Fixtures are never findings.** Every fixture row carries `"source": "SAMPLE — NOT NASA DATA"`, the UI shows a SAMPLE DATA banner whenever it sees that, and fixtures are removed from the deployed demo before Sunday 16:00.

Files over about 20 MB: discuss before committing.
