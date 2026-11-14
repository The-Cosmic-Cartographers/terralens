# Case Files (NAS-42)

Three worked examples, each built from output that exists in `data/results/` today. Every
number below is copied from the JSON named beside it; nothing is estimated, rounded up, or
filled in from a paper.

**Provisional.** The Lineup holds only air temperature, so each region's correction covers one
test and the adjusted p-values below equal the raw ones. They will change when the other four
variables join the correction. The three verdicts should hold (the p-values are far below
0.05), but every number here must be re-read from the files on Sunday (D16) before it is used
on the project page.

**Wording sign-off: pending Nandini.** The copy is drafted to the rules in doc 12: no
attribution, no causal language, no mention of expected directions, and no claim stronger
than the verdict.

Substitutions and limits, stated up front:

- The ticket's candidate pairs (Ireland vs Iberia, wet vs dry) need precipitation, soil
  moisture or evapotranspiration. Those series do not exist yet, so all three cases use
  air temperature, the only variable with real output.
- The Dublin–Delhi pollution pair needs OMI NO2, which has no data (NAS-27). That case is
  replaced by the Sahel record-shape case below.
- "No clear trend" is covered by Case 2, which uses the window output rather than a Lineup
  row, because all three Lineup rows are significant.

---

## Case 1 — Is everywhere warming at the same speed?

**Plain language**

> All three places have warmed since 1981. They have not warmed at the same rate. The
> south-western United States warmed about twice as fast as Ireland, and almost three times
> as fast as the Sahel; its interval sits above both of theirs, so the difference is large
> relative to the uncertainty. Ireland's and the Sahel's intervals overlap, and this page
> reports no formal test between two places, so the product does not order those two.

**Numbers**

| Place | Rate | 95% interval | Adjusted p | Period | Verdict |
|---|---|---|---|---|---|
| US Southwest | +0.46 °C per decade | +0.33 to +0.59 | 1.1 × 10⁻¹¹ | 1981-01 – 2025-12 | significant |
| Ireland | +0.21 °C per decade | +0.12 to +0.31 | 1.5 × 10⁻⁵ | 1981-01 – 2025-12 | significant |
| Sahel | +0.17 °C per decade | +0.04 to +0.29 | 1.0 × 10⁻³ | 1981-01 – 2025-12 | significant |

Ireland's interval (+0.12 to +0.31) and the Sahel's (+0.04 to +0.29) overlap, so the two are
not ordered — and no formal between-region test is reported here, which is why the copy says
"does not order" rather than "is not different". The US Southwest's interval starts above the
top of both.

Source: `data/results/lineup/{us_southwest,ireland,sahel}.json`, family `lineup:<region>`.
540 monthly observations each, no missing months.

**Caveat, in the app's words**

> These are three boxes of very different size and climate, not a global ranking. A faster
> rate here does not mean this is the fastest-warming place on Earth.

**Why this case earns its place:** it is the one place the product legitimately compares
places — same variable, same window, same method, same correction family per region.

---

## Case 2 — Can the same place look flat?

**Plain language**

> The same Irish temperature series gives two different answers depending on the years you
> look at. Over the full record the warming is clear. Over 1986–2015 the estimate is
> smaller and the interval includes zero, so the honest answer for that window is: no clear
> trend. Neither answer is wrong; the second one is what "not yet detectable" looks like.

**Numbers**

| Window | Rate | 95% interval | Adjusted p | Verdict |
|---|---|---|---|---|
| 1981 – 2025 | +0.21 °C per decade | +0.12 to +0.31 | 1.5 × 10⁻⁵ | significant |
| 1986 – 2015 | +0.14 °C per decade | −0.05 to +0.35 | 0.18 | no clear trend |

Source: `data/results/windows/merra2_m2tmnxslv/ireland.json` (30-year windows) and
`data/results/lineup/ireland.json`.

**Caveat**

> A shorter window has fewer years to work with, and a quiet stretch inside a warming record
> is expected. "No clear trend" means this window cannot separate a trend from noise — not
> that the place stopped warming.

**Why this case earns its place:** it is the "No clear trend" example the ticket asks for,
and it teaches the reader how to read the verdicts instead of the slopes.

---

## Case 3 — Where does the Sahel record split?

**Plain language**

> The Sahel series is not a straight line. The single year that best splits the record is
> 1995: the average before it is about 27.4 °C and after it about 28.0 °C. The overall trend is
> already a significant warming, and a steady warming also splits a record in the middle, so we
> do not call this a step change. It describes the shape of this record; it says nothing about
> what caused it and does not predict that it continues.

**Numbers**

| Quantity | Value |
|---|---|
| Change point (most likely year) | 1995 |
| Mean before | 27.42 °C |
| Mean after | 28.01 °C |
| Difference | +0.59 °C |
| p for the split | 0.0035 |
| Record | 1981-01 – 2025-12, 540 months |
| Overall rate | +0.17 °C per decade (adjusted p 1.0 × 10⁻³) |

Source: `data/results/lineup/sahel.json` (`change_point`) and
`data/results/windows/merra2_m2tmnxslv/sahel.json`.

**Caveat**

> The change point is descriptive: it is the year that best splits this record, chosen after
> looking at the data. Because the overall trend is significant, it is not presented as a step
> change (D25), and it is not a detected break with a physical cause attached.

**Why this case earns its place:** it shows the product distinguishing "the trend" from "the
shape of the record" — and it keeps D25's rule that diagnostics are descriptive only.

---

## What each case must not say

- No "because of", "driven by", "due to", "caused by" — nothing in this output supports a cause.
- No "step change" or "jump" for a row whose verdict is "Significant trend" (D25): a steady
  trend also peaks mid-record in the change-point test.
- No "fastest-warming", "worst", "dangerous" — no ranking beyond the three boxes shown.
- No mention of what doc 11 expected to find; the reader gets the result, not the hypothesis.
- No decimal places beyond the ones above: the slope is meaningful to two, the p-value to two
  significant figures.
