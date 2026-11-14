# Methodology, uncertainty and limitations (NAS-49)

Copy blocks for the app and the Space Apps project page.

**Division of labour between the pages:** `docs/sensitivity-notes.md` is the evidence — it is generated from the processed series and carries the current numbers. This page is the wording. If a sentence here quotes a number, that number must be re-read from `data/results/` before publishing (see the checklist at the bottom).

---

## 1. App — method box

Paste as three paragraphs; the frontend shows it in a collapsible panel next to the verdict.

> **How the trend is measured.** Each month is compared with its 1991–2020 normal for that calendar month, and the seasonal Mann–Kendall test asks whether the resulting anomalies rise or fall consistently through the record. Because neighbouring months are not independent, the test's variance is corrected with the Hamed–Rao method using the lag-1 autocorrelation of the residuals — without it a slow-moving series would look more certain than it is. The slope is Sen's slope, the median of all pairwise slopes, reported per decade with a 95% confidence interval.
>
> **What we check.** The same test on annual means is shown beside it as a sensitivity check: if the monthly and annual results disagree, the row is fragile and we say so. Every verdict uses the Benjamini–Hochberg adjusted p-value for its family — a region's five rows, or one variable across regions — so the chance of a false positive does not grow with the number of rows on screen.
>
> **What a verdict means.** *Significant trend* means the adjusted p-value is below 0.05. *Weak evidence* is 0.05–0.10 and is not a claim. *No clear trend* means this record cannot show one — not that nothing changed. *Not enough data* means the coverage rules failed before any test ran, so no slope and no p-value are reported at all.

## 2. App — verdict legend

One line each, shown beside the pill.

| Verdict | Line |
|---|---|
| Significant trend | The record shows a consistent change; adjusted p < 0.05 |
| Weak evidence | Suggestive, but not proven; adjusted p 0.05–0.10 |
| No clear trend | This record cannot show one — that is not the same as "no change" |
| Not enough data | Too few years or too many missing months; the result is withheld, not guessed |

## 3. App — limitations panel

> * MERRA-2 is a model reconstruction constrained by observations, not a thermometer. A trend in it is a trend in the assimilated system.
> * A box average hides what happens inside the box.
> * Every result belongs to the years shown on its card; the Time Machine exists because that choice matters.
> * "No clear trend" is not "no change". With 21–45 years and this much year-to-year noise, many real changes are not detectable yet.
> * These numbers describe what happened. They do not say why, and they do not predict what comes next.

---

## 4. Project page — "How the numbers are made"

> Each variable is averaged over the region's box to give one value per month. We remove the seasonal cycle by subtracting each calendar month's normal, using 1991–2020 where the record allows and the full record where it does not (GLDAS starts in 2000, IMERG in 2001).
>
> The trend test is the seasonal Mann–Kendall test, which does not assume the data follow a bell curve and is not thrown by a single extreme month. We correct its variance for serial correlation with the Hamed–Rao method. The size of the trend is Sen's slope — the median of all pairwise slopes — with a 95% confidence interval, and we also express it as a multiple of the normal year-to-year swing so a statistically clear but tiny change is not mistaken for a large one.
>
> Because five variables are tested per place, and several places per variable, we apply Benjamini–Hochberg within each family and base every verdict on the adjusted p-value. Raw p-values remain visible in the detail view.
>
> Before any test runs, coverage rules decide whether a row can be tested at all: a month counts as missing when less than half its area is valid, and a row is withheld below ten complete years or above 20% missing months. A withheld row is shown with its reason and no statistics, because "not enough data" must never be displayed as "no trend".
>
> For every row we also precompute the same test across every start/end pair at least ten years apart, which is what the Time Machine slider reads. A window that would span a year without all twelve months is not offered at all, rather than being computed from a discontinuous record. For rows that are not significant, we report how many years of record a trend of that size would need to be detected (Weatherhead et al., 1998). That is a statement about evidence, not a forecast.

## 5. Project page — "Uncertainty"

> A confidence interval and a p-value answer different questions. The interval says how precisely we know the size of the change; the p-value says how easily a change this consistent could have arisen from noise alone. We show both, and neither is allowed to stand without the other.
>
> Serial correlation matters here. In the rows computed so far the lag-1 autocorrelation of monthly anomalies is about 0.31–0.35, and the Hamed–Rao correction roughly doubles the variance of the test statistic. Without it, the same data would look considerably more certain than it is.
>
> The period matters too. Over all windows of at least ten years, the share that reach p < 0.05 ranges from about a third to two thirds depending on the region, and window slopes span roughly −0.7 to +1.7 °C/decade for 2 m temperature. That spread is not a defect in the method — it is the honest width of the answer, and it is why every card prints its own years.
>
> Where a trend is real but too small for the record, we say how many years would be needed rather than implying that nothing is happening.

## 6. Project page — "Honest limits"

> * **Reanalysis is not observation.** MERRA-2 and GLDAS combine a model with assimilated observations; changes in what is assimilated can create artificial steps, aerosol most of all. Satellite rows (IMERG precipitation, OMI NO₂) sit beside model rows for that reason, and every row carries a badge.
> * **Box averages hide internal variation.** A trend for "Iberia" is not a trend for every valley in Iberia.
> * **Every result is period-specific.** Each row prints its own window; the Time Machine shows how much the answer depends on it.
> * **"No clear trend" is not "no change".** It means this record cannot demonstrate one.
> * **One change point at most.** The Pettitt diagnostic looks for a single level shift, is conservative on short records, and never sets a verdict.
> * **Multiple testing is corrected, not eliminated.** Benjamini–Hochberg controls the expected share of false discoveries within a family; it does not make any single row certain.
> * **Nothing here is attributed or forecast.**

## 7. What TerraLens does not do

* It does not say why a trend happened.
* It does not predict future values, or when a threshold will be crossed.
* It does not rank places by "danger" or "severity" — ranks are by strength of evidence, not by importance.
* It does not fill gaps by interpolation, and it does not hide a withheld row.
* It does not compare periods that differ without saying so.

## 8. Wording rules (scientific QA, NAS-48)

| Say | Do not say |
|---|---|
| "Air temperature rose about 0.21 °C per decade over 1981–2025" | "Ireland is warming because of climate change" |
| "The record shows a significant increase" | "We proved the increase is real" |
| "No clear trend in this record" | "Nothing is changing" |
| "Would need about 60 years of record to detect a trend this size" | "Will be significant by 2040" |
| "Weak evidence — not a claim" | "Almost significant" or "borderline significant" |
| "Consistent with a drying trend" | "Caused by", "driven by", "due to" |
| "Not enough data" | "No trend" (for a withheld row) |
| "Adjusted p = 0.004 (raw 0.0009)" | "p = 0.004" alone, or "p = 0.000" |
| "Over 2001–2024" | "Currently" or "today" |

Two hard rules for QA: a p-value never appears without its period and observation count, and a withheld row never appears with a slope.

## 9. Before publishing — numbers must come from the pipeline

Tick each one against `data/results/`, never from memory or from this page:

- [ ] slope per decade and its 95% CI
- [ ] raw p and adjusted p
- [ ] period start and end, and observation count
- [ ] effect size ("about k× the normal swing")
- [ ] detectability, for non-significant rows only
- [ ] verdict label and any caveat, including `record_long_enough_but_not_significant`
- [ ] product badge and dataset version from `provenance.json`

Regenerate the evidence page with `python -m analysis.sensitivity` after any new series lands; the numbers in this document must then be re-read, not assumed.
