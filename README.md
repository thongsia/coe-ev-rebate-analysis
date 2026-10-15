# Do electric car rebates make people bid more for COEs?
_Disclaimer: This analysis is done by AI_

Singapore's EV rebates (VES, EEAI, and their predecessors) can save car
owners up to tens of thousands of dollars. A natural question: **do those
rebates push up the prices people pay to get a car-ownership quota (COE)?**
The idea would be that rebates make EVs cheaper to own, more people want
them, bidding demand rises, and COE prices go up.

This repo contains a data-driven study of exactly that question, using a full
decade of official COE auction results, car registration data, and the
verified real rebate policy timeline.

## The short answer

The honest result has two parts:

- **Over the whole decade (2016–2025): no detectable effect.** When EV rebate
  rules changed, car prices jumped — but so did prices in categories where
  *no EV rebate exists at all* (Figure 2). That's a market-wide event (a tax
  rule and a car-category threshold changed in Jan 2022), not evidence that
  the rebates did anything.
- **In the EV era (2022–2025): a price reaction to the 2024 rebate cut.**
  When the government cut the maximum rebate from S$45k to S$40k in Jan 2024,
  the average EV-category COE price moved in the same direction as the
  rebates did — and categories without rebates did not show the same pattern.
  This is real, but small-sample and **associational**: it shows prices and
  rebates moved together, not that rebates *caused* the price change.

Bottom line: **we cannot find convincing evidence that EV rebates make
bidders bid more.** The study deliberately says "we can't detect it" rather
than pretending to measure a precise effect that the data can't support.

The full write-up, with all statistics, is in [`docs/REPORT.md`](docs/REPORT.md).

## The data

Three public, free datasets from [data.gov.sg](https://data.gov.sg):

| Data | What it tells us |
|---|---|
| COE bidding results (2010 → 2026) | Every auction's final price, how many people bid, and how many quotas were sold, by car category |
| Monthly car registrations (2016 → 2025) | How many electric vs hybrid vs petrol cars were registered each month |
| Consumer price index (monthly) | Inflation, so we can compare prices in "real" (inflation-adjusted) dollars |

Two data caveats worth knowing:

- **EV registration counts are lower bounds.** About half of the monthly
  registration rows don't carry a car-count number (the field went blank more
  often over time), so EV totals are reported with a monthly coverage rate.
- **Category A is not an "EV category".** It's the small-engine car
  category (engines up to 1600cc and power output up to 97kW / 130bhp;
  fully electric cars up to 110kW) — most EVs fit, which is why EVs land
  in it. That's why the study looks at the whole decade, not just
  "EV months".

## What the rebate policy actually did

The analysis uses the **verified real policy timeline** (LTA/NEA
announcements and published rate sets):

| When | What happened | Max rebate available |
|---|---|---|
| 2016–2017 | CEVS (old clean-car scheme) still in force | ~S$20k (estimate) |
| Jan 2018 | CEVS ended; new VES scheme began | S$25k |
| Jan 2021 | New EEAI incentive launched on top of VES (45% off the registration tax, capped at S$20k) | S$45k total |
| Jan 2022 | Minimum tax on electric cars dropped to zero — EVs could now use the full rebate caps | S$45k (fully usable) |
| Jan 2024 | EEAI cap cut from S$20k to S$15k | S$40k total |

That's the key to the whole design: the rebate amount **changed four times**
over the decade, giving the statistics something to bite on. The full timeline
with sources is in `tables/rebate_timeline.csv`.

## What we found

### 1. The big 2022 price jump was not caused by the rebates

Category A prices jumped sharply in Jan 2022 (Figure 1) — the same month
electric cars stopped paying a minimum registration tax and the category's
engine-power threshold was raised. The obvious suspects are those two rules,
not the rebates.

**Figure 1.** Category A COE clearing price, 2016–2025, with the verified
policy changes marked.

![Category A COE prices over time, nominal and inflation-adjusted, with the verified policy changes marked](charts/01_price_regime.png)

*Top: nominal prices. Bottom: inflation-adjusted prices. Dotted gray lines
mark the verified policy changes; the dashed red line marks the Jan 2022
tax/threshold change.*

The proof: **car categories where no EV rebate ever applies showed the same
jump** (Figure 2). If rebates had caused the price rise, we wouldn't see it
in cars that can't get a rebate.

**Figure 2.** The negative-control test: % price jump by car category —
2022-01 (top) and 2024-01 (bottom).

![Negative-control check: % price jump by category, 2022-01 and 2024-01](charts/02_negative_controls.png)

*Top: the Jan 2022 jump shows up in the rebate-free categories C, D and E as
well — a market-wide event, not a rebate effect. Bottom: the 2024 cap cut
moves Category A more than C/D do (E comparably — a single category).*

### 2. In the EV era, prices did respond to the 2024 rebate cut

Because the rebate changed *again* in Jan 2024 (S$45k → S$40k), the
2022–2025 window can be estimated on its own — the rebate amount varies
within it, so the statistics have something to work with. In that window:

- For every extra S$1,000 of maximum rebate, the average Category A price was
  about **S$4,100 higher** — a statistically clear association (p < 0.001 by
  several measures, nominal and inflation-adjusted alike).
- Rebate-free categories did **not** show the same 2024 move (Figure 2,
  bottom panel), so this is plausibly EV-relevant.
- But the window has only 41 months and two rebate levels, so this is a
  **low-power association, not a measured causal effect**. It's evidence the
  price system responded to the rebate cut — not a number to quote as "how
  much rebates raise prices".

### 3. Rebates did not make more people bid

If the rebate story were true, we'd expect bidding demand in Category A to
rise with rebate generosity. It didn't: the bidding numbers show no
consistent, same-direction link to the rebate changes (in the EV era the
statistical sign is even backwards, which is most consistent with noise and
mixing in non-EV demand — Category A is still mostly non-EV cars). Figures 3
and 4 show the EV uptake and the price-vs-bids relationship directly.

**Figure 3.** Electric car registrations and their share of new-car sales,
with the data-coverage lower bound.

![EV registrations and their share of new cars, with the data-coverage lower bound](charts/03_ev_demand.png)

*Electric car registrations and their share of new-car sales from 2022
(when the official EV label first appeared). The dashed line is a lower bound
due to missing counts.*

**Figure 4.** Category A COE price (left axis) vs number of bids received
(right axis), over the same period.

![Category A COE price (left axis) vs number of bids received (right axis)](charts/04_price_demand_dual.png)

*Price and bidding demand over the same period — note how weakly connected
the two are.*

### 4. Prices and bidding demand barely track each other

A basic requirement for "more bidding → higher prices" is that price and
bids actually move together. Across the decade they mostly don't (Figure 5).

**Figure 5.** Each dot is a month: Category A price vs bids received, with
the best-fit line and its uncertainty band.

![Each dot is a month: Category A price vs bids received, with the best-fit line and uncertainty band](charts/05_scatter_fit_ci.png)

*The fit line is nearly flat — more bids did not reliably mean higher prices.*

### 5. The "rebate → more bidders → higher price" chain is broken

We also decomposed the effect the way the hypothesis describes: rebate →
bidding demand → price. The middle link (rebate affecting bidding) is null,
so the whole chain is null — **whatever small price movement exists is not
routed through more bidding** (Figure 6).

**Figure 6.** The hypothesized chain — rebate → bidding demand → price —
with the estimated size of each step for both time windows.

![The hypothesized chain: rebate → bidding demand → price, with the estimated size of each step for both time windows](charts/06_mediation_diagram.png)

*The indirect (via-bidding) path is statistically indistinguishable from
zero in both time windows.*

### 6. Looking at each policy change individually doesn't help either

An "event study" examines prices around each of the four policy changes.
Every single one shows the price was already drifting in that direction
*before* the policy started (Figure 7) — the signature of the long-run COE
price trend (plus the pandemic-era dip in 2020), not of the policy itself.
The estimated effects are therefore reported as bounds, not point estimates.

**Figure 7.** Estimated price changes around each of the four policy
changes, with uncertainty bars.

![Estimated price changes around each of the four policy changes, with uncertainty bars; the pre-change "leads" should be zero if the policy caused the move](charts/07_event_study.png)

*One panel per policy change (2018 VES, 2021 EEAI, 2022 tax floor, 2024 cap
cut). The left side of each panel (months *before* the change) already shows
large non-zero moves — the pre-trend problem.*

### 7. What we can and can't claim

- **Can claim:** no detectable EV-specific effect of the rebates on COE
  prices or bidding across the decade; the 2022 price jump was market-wide;
  prices and bidding demand are weakly related; the via-bidding chain is
  broken.
- **Can't claim:** a precise "rebates raise prices by X" number. The rebate
  policy was itself *set in response to* EV demand (policy and outcome move
  together by construction), the samples are small, and the one detected
  association sits in a 41-month window with two rebate levels.

## Under the hood (for the curious)

**How the study works.** The design's core trick: rebates changed level four
times over 2016–2025, so months can be compared across rebate levels.
Everything is estimated on the full decade (110 months with auctions), and
the 2022–2025 "EV era" is estimated separately too, because the rebate amount
changes *within* that window (the 2024 cap cut). A guard module checks this
programmatically before any result is
produced (`src/05_scope_guard.py`).

**Reproducibility.** Every number in the report traces to a file: raw data in
`data/raw/` (with a provenance record tying each download to its source),
processed panels in `data/processed/`, one CSV per table in `tables/`
(26 CSVs), seven charts in `charts/` (Figures 1–7), and the reports in `docs/`. A
verification module re-checks row counts, citations, and that all 112 report
figures match the tables (the current run passes 9/9 checks).

**Re-running it.**

```bash
python3 -m pip install pandas statsmodels matplotlib
cd <repo root>
python3 src/01_fetch.py         # re-download the three data.gov.sg stores (fails on count mismatch)
python3 src/05_scope_guard.py   # build the panel, run all exhibits, audit the scope rules
python3 src/13_charts.py        # regenerate the charts
python3 src/14_verify.py        # re-run the 9 verification checks
python3 src/15_report.py        # regenerate both reports from the tables
```

**Repository layout.**

```
README.md                  ← this file
docs/REPORT.md             ← full report
docs/STATS_SUMMARY.md      ← one-page statistics summary
data/raw/                  ← source CSVs + provenance.csv
data/processed/            ← monthly panels
tables/                    ← one CSV per reported table
charts/                    ← the seven charts shown above (Figures 1–7)
src/                       ← 18 ordered Python modules (fetch → panel → exhibits → verify → report)
```

---

*Analysis window: 2016-01 → 2025-05 (with COE-only descriptive extension to
2026-10). Built with the KAKIS research→plan→synthesize→execute pipeline.
All figures in the reports trace to `tables/*.csv`.*
