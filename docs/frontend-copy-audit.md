# Frontend copy and number audit (NAS-48)

Audit of `frontend/nasa-earth-trends/` as merged from PR #23, against the
wording rules in `docs/methodology.md` §8 and the label rules in D23/D24.

**Scope honesty:** the result views are still placeholders, so no trend number,
p-value, interval, coverage fraction or detectability figure is rendered
anywhere yet. The rules that govern those can be listed but not tested. What
follows is everything that *is* on screen.

## Blocking — wrong the moment real data ships

| # | Where | What it says | Why it is wrong | Fix |
|---|---|---|---|---|
| F1 | `src/components/SampleDataWarning.jsx`, rendered unconditionally at `HomePage.jsx:91`, `ExplorePage.jsx:29`, `VariableDetailPage.jsx:30`, `ComparePage.jsx:19`, `CaseFilesPage.jsx:18` | "SAMPLE DATA — NOT NASA DATA. Fixture values are for interface development only." | The banner is always on. With the real export, the site would tell every visitor that NASA data is fake fixtures. | Render it only when `health.json`'s `data_version` contains `SAMPLE`. The component should take that value, not decide for itself. |
| F2 | `src/pages/ExplorePage.jsx:58`, `src/pages/VariableDetailPage.jsx:27,58` | `ProductBadge type="reanalysis"`, and the literal "Model reanalysis" | Hardcoded. Three of the five rows are not reanalysis: soil moisture and evapotranspiration are `land_model`, precipitation is `satellite`. Every GLDAS and IMERG row would carry a false badge — the exact claim the badge exists to make. | Pass each row's own `product_type`. Never default to `reanalysis`. |
| F3 | `src/pages/VariableDetailPage.jsx:66` | "The current backend contract does not expose a variable-result endpoint." | Untrue: `/trend`, `/series`, `/windows`, `/lineup` and `/compare` all exist, and the static export carries them. A judge reading this concludes the app is unbuilt. | Delete the sentence; replace the empty state with the real result once the data client reads it. |
| F4 | `src/pages/ExplorePage.jsx:50` | `0{index + 1}` printed as a rank, on a page titled "The Lineup" asking "Which environmental signals are moving most clearly?" | The number is catalogue order, not evidence. A ranking by array position is the one thing D23 forbids, and it will read as a finding. | Rank from the lineup rows: adjusted p first, then effect size, as `analysis/run.py` already orders them. |
| F8 | `src/services/dataClient.js` | `VITE_STATIC_DATA_BASE_URL` defaults to `/data/fixtures` | If the variable is not set at build time, the deployed site serves the SAMPLE fixtures while looking finished. | Default to `/data`; keep fixtures on an explicit opt-in. |

## Wording — minor, judge-visible

| # | Where | Now | Should be |
|---|---|---|---|
| F5 | `src/components/VerdictBadge.jsx:2` | "Significant" | "Significant trend" (D23's label; the whole app turns on this word) |
| F6 | `src/pages/HomePage.jsx:69` | "ranked by their observed trend over the measured period" | "ranked by how strong the evidence is" — ranking is by adjusted p, not by slope size |
| F7 | `src/pages/VariableDetailPage.jsx:11` | `variableId.replaceAll('_', ' ')` → the slug "t2m" as the page title | The catalogue label, "Air temperature (2 m)" |

## Passed

* Hero: "No forecasts. No claims about causes." — matches D24 exactly.
* `ProductBadge` maps all three real `product_type` values when handed the value (`reanalysis`, `land_model`, `satellite`).
* Verdict labels "Weak evidence", "No clear trend", "Not enough data" match D23.
* The detail page states plainly that no scientific result is being invented while the view is empty — good instinct, stale reason (F3).

## Cannot be checked until the result views render data

Each of these is a rule the app must satisfy, and each is currently untestable
because no number is on screen:

- [ ] no p-value or slope without its period and observation count
- [ ] a withheld row shows its reason and **no** statistics
- [ ] `coverage_fraction: null` reads "coverage unknown", never 0%
- [ ] "p = 0.000" never appears; very small p renders as `< 1e-300` or similar
- [ ] detectability reads "would need about N years of record", never a forecast
- [ ] the change point is called a step change **only** when the verdict is not significant
- [ ] the 95% interval is shown with its direction and unit

## Sign-off

**Not signed off.** Five blocking findings (F1–F4, F8) would each put a false
statement in front of a judge. The number rules cannot be assessed until the
detail, Lineup and Time Machine views read the exported results.
