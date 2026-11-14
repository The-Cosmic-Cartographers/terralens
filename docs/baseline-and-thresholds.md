# What 1.5 °C means — static explainer card

**Status:** copy ready. It is static text: it computes nothing, calls no endpoint, and must
never be attached to a region card. Frontend places it (About/help); Nandini owns the wording.

---

## The card (short form, for the app)

**The 1.5 °C figure is not a single hot year**

> Global temperature limits are measured over 20 years, against the 1850–1900 average.
> One year above the line is not the line being crossed. 2024 was the first calendar year
> above 1.5 °C, and 2026 is expected to be the second. Measured the way the IPCC measures
> it — a 20-year average — 1.5 °C is expected in the early 2030s, and confirmed only about
> a decade later.

*Sources: IPCC AR6; WMO, State of the Global Climate 2024; C3S, 11 November 2026.*

Placement rule: the card sits beside the product's own numbers, never inside them. No region
card, no Lineup row, no Case File carries a "1.5 °C" badge.

---

## The long form (project page / judging Q&A)

**"Has the world passed 1.5 °C?"**

> Not in the sense the Paris Agreement means. 2024 was the first calendar year above 1.5 °C
> relative to 1850–1900, and 2026 is virtually certain to be the second, with 2023–2026 the
> first four-year average above it. But the IPCC defines a warming level on a 20-year running
> average, and the "year of exceedance" is the midpoint of the first such period — so the
> level is expected in the early 2030s and is confirmed roughly ten years after that. A single
> year also carries about ±0.25 °C of internal variability.

**"Why don't your regions use the pre-industrial baseline?"**

> Because our record starts in 1981. MERRA-2 does not reach 1850, so a pre-industrial anomaly
> for a region would be an imported constant, not a measurement. C3S converts global anomalies
> from 1991–2020 to 1850–1900 by adding 0.88 °C; that offset is a global figure, and applying
> it to a regional box would dress up a constant as a finding. Our regions stay on 1991–2020
> and the card explains the difference.

**"Where did the industrial baseline come from, if industrialisation started earlier?"**

> It is a data compromise, not a historical claim. 1850–1900 is the earliest period with
> near-global observations, which is why IPCC uses it. Hawkins et al. (2017) argue 1720–1800
> is the more defensible pre-industrial period and estimate it was 0.55–0.80 °C cooler than
> 1986–2005; other work puts the extra pre-1850 warming at 0.0–0.2 °C (Schurer et al. 2017)
> and about 0.05 °C from 1750 to 1850–1900 (Haustein et al. 2017). Proxy evidence has the
> 1750s statistically indistinguishable from 1850–1900. And industrial-era warming appears to
> have begun in the 1830s in the tropics and Southern Ocean (Abram et al. 2016) — earlier than
> the baseline's start date.

---

## What this card must not say

- Not "we have passed 1.5 °C", not "the limit is breached", not "it is too late".
- Not "this region is at 1.5 °C" or any per-region threshold, ever.
- Not a live number computed from our data — it is a fixed quotation of published figures.
- Not "2026 proves", "2024 proves": single years illustrate the definition, they do not settle it.
- No attribution or causal claim about any particular event.

---

## Implementation constraints

- Static string in the frontend bundle. No API call, no new contract field, no pipeline change.
- No colour-only meaning, reachable by keyboard, readable at default zoom.
- Dates and figures are frozen to the sources below; if C3S publishes a new annual statement,
  update the card and this file together, not one of them.
- If the figure ever changes (for example, a later C3S bulletin), the citation line changes with
  it — the app must never show a number without the source and date beside it.

---

## Sources

- IPCC AR6 WGI, Summary for Policymakers: 1.09 °C [0.95–1.20] for 2011–2020 relative to
  1850–1900; warming levels defined on 1850–1900. https://www.ipcc.ch/report/ar6/wg1/
- IPCC AR6 SYR, footnote on 20-year running averages and ±0.25 °C single-year variability.
  https://www.ipcc.ch/report/ar6/syr/
- WMO, *State of the Global Climate 2024*: the year of exceedance is the midpoint of the first
  20-year period above the level, confirmed about ten years later.
  https://wmo.int/publication-series/state-of-global-climate-2024
- C3S, 11 November 2026: 2026 virtually certain to exceed 1.5 °C, second year after 2024;
  2023–2026 the first four-year average above it; 0.88 °C conversion from 1991–2020 to 1850–1900.
  https://climate.copernicus.eu/2026-and-4-year-global-temperature-average-track-exceed-15degc-above-pre-industrial-levels
- Hawkins et al. (2017), *Estimating Changes in Global Temperature since the Preindustrial
  Period*, BAMS 98(9). https://doi.org/10.1175/BAMS-D-16-0007.1
- Schurer et al. (2017); Haustein et al. (2017); PAGES 2k Consortium (2019) — summarised in
  IPCC AR6 WGI Ch. 1, which reserves "pre-industrial" for the period around 1750.
- Abram et al. (2016), *Early onset of industrial-era warming across the oceans and continents*,
  Nature 536, 411–418. https://doi.org/10.1038/nature19082
