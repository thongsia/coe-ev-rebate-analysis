# Do EV rebates drive more bidding demand for COEs?

_Disclaimer: This analysis was prompted by a human, then initially designed and carried out by an AI agent (Hermes + Qwen3.8-27B), and finally shaped and edited collaboratively between the two._

Singapore's EV rebates (VES, EEAI, and their predecessors) can save car
owners up to tens of thousands of dollars. A natural question: **do those
rebates push up COE prices?**
The idea would be that rebates make EVs cheaper to buy, more people want
them, bidding demand rises, and COE prices go up.

This repo contains a data-driven study of exactly that question, using a
full decade of official COE auction results (2016-01 to 2025-05), car
registration data, and the verified real rebate policy timeline.

**How to read this file:** this README stands on its own — it contains the
question, the data, the method in plain language, and the main results
with the statistics and charts behind them. For second-level detail —
full model specifications, every coefficient and confidence interval,
sensitivity checks, and the automated verification checklist — see
[`docs/REPORT.md`](docs/REPORT.md) (the full report) and
[`docs/STATS_SUMMARY.md`](docs/STATS_SUMMARY.md) (a one-page statistics
summary). Every number in this README is quoted from the tables in
`tables/`, and the automated verifier re-checks all of them on every run.

## 1. The short answer

The honest result has two parts:

- **Over the whole decade (2016–2025): no detectable effect.** When the
  Jan 2022 tax rule changed, car prices jumped — and the two categories
  where *no EV rebate exists at all* (C: goods vehicles & buses; D:
  motorcycles) split in their reaction: D jumped more than the EV category
  did, and C moved the other way (Figure 2). That split means the test is
  inconclusive on its own — but the decisive fact is that what changed in
  Jan 2022 was a tax rule (EVs' minimum registration tax dropped
  to zero), not a change to the rebate; the separate 97→110 kW category threshold
  change followed in May 2022. The estimated Jan 2022 price effect is
  +S$3,700 (95% CI −S$180 to +S$7,600; p = 0.061) — not statistically
  robust, so it can't be credited to the rebates either way.
- **In the EV era (2022–2025): a price reaction to the 2024 rebate cut.**
  When the maximum rebate fell from S$45k to S$40k in Jan 2024, the
  average EV-category COE price moved with it: for every S$1,000 of
  maximum rebate, the average Category A price was about **S$4,090
  lower** (95% CI S$2,060 to S$6,120; p = 0.00008, robust to
  inflation-adjusted dollars at p = 0.00007). The rebate-free categories
  (C and D) moved far less than the car categories (Figure 3), so this
  association is plausibly EV-relevant. But the window has only 41 months
  and two rebate levels, so this is a **low-power association, not a
  measured causal effect**: it shows prices and rebates moved together,
  not that rebates *caused* the price change.

Bottom line: **we cannot find convincing evidence that EV rebates
drive more bidding demand.** The study deliberately says "we can't detect
it" rather than pretending to measure a precise effect that the data can't
support.

## 2. The data

Three public, free datasets from [data.gov.sg](https://data.gov.sg):

| Data | What it tells us |
|---|---|
| COE bidding results (2010 → 2026) | Every auction's final price, how many bids were received, and how many quotas were sold, by car category. In practice the bids are placed mostly by car dealers on their customers' behalf, as part of the car sale — not by the customers themselves |
| Monthly car registrations (2016 → 2025) | How many electric vs hybrid vs petrol cars were registered each month |
| Consumer price index (monthly) | Inflation, so we can compare prices in "real" (inflation-adjusted) dollars |

Data caveats worth knowing:

- **Bid counts need careful parsing.** The raw COE results file stores
  bid counts as text, and from 2023-10 on it writes large numbers with
  thousands separators (e.g. "1,039"), which a naive parse would silently
  read as 0. All analysis in this repo therefore uses `catA_bids_received_clean`,
  rebuilt in `src/00_data.py` from the raw file (separators stripped,
  monthly sums recomputed); it is non-zero for all 110 COE months and is
  re-verified by `src/14_verify.py` on every run.
- **EV registration counts are lower bounds.** Only about one in four of
  the monthly registration rows carries a car-count number (mean coverage
  23% across 2022-07..2025-05, ranging from 18% to 33%, and falling over
  time), so EV totals are reported as a lower bound with a monthly
  coverage rate.
- **Category A is not an "EV category."** It's the small-engine car
  category (engines up to 1600cc and power output up to 97kW / 130bhp;
  EVs up to 97kW before May 2022, and up to 110kW from
  the May 2022 threshold change on) — most EVs fit, which is why EVs
  land in it. That's why the study looks at the whole decade, not just
  "EV months".
- **The five categories (per LTA):** A: small cars (≤1600cc, ≤97kW; EVs
  ≤110kW from May 2022). B: large cars (>1600cc or >97kW — i.e. high-power
  EVs land here). C: goods vehicles & buses. D: motorcycles. E: open — any
  vehicle except a motorcycle, so EV cars *can* bid here. Only C and D are
  truly free of EV rebates; B and E are "contaminated" (EVs can be in
  them), which is why the negative-control test (Figures 2–3) relies on
  C and D.

## 3. What the rebate policy actually did

The analysis uses the **verified real policy timeline** (LTA/NEA
announcements and published rate sets; every row in
`tables/rebate_timeline.csv` carries its source):

| When | What happened | Max rebate available |
|---|---|---|
| 2016–2017 | CEVS (old clean-car scheme) in force | S$30k (revised CEVS top band) |
| Jan 2018 | CEVS ended; new VES scheme began | S$20k |
| Jan 2021 | Enhanced VES (top band S$25k) + new EEAI incentive on top (45% off the registration tax, capped at S$20k) | S$45k total |
| Jan 2022 | Minimum registration tax on EVs dropped to zero — a **tax rule, not a rebate**; the full rebate caps became usable | S$45k (dose unchanged) |
| May 2022 | Category A engine-power threshold for EVs raised from 97 kW to 110 kW, effective from the May 2022 bidding exercise (LTA, 14 Apr 2022) — a **quota rule, not a rebate** | S$45k (dose unchanged) |
| Jan 2024 | EEAI cap cut from S$20k to S$15k | S$40k total |

That's the key to the whole design: the rebate amount **changed three
times** (2018, 2021, 2024), giving the statistics something to bite on.
The two non-rebate rule changes (Jan 2022 tax, May 2022 threshold) are
tracked separately as controls, because they also move prices.

## 4. What we found

### 4.1. The big 2022 price jump was not caused by the rebates

Category A prices rose about **21%** in early 2022 — from S$57,906 in
Dec 2021 to S$70,028 in Mar 2022, roughly S$12,100 above the Dec 2021
level (Figure 1), and the rise held after adjusting for inflation
(+20.9% in real terms). The timing lines up with the Jan 2022 tax rule
(EVs stopped paying a minimum registration tax) and, four
months later, the May 2022 engine-power threshold change. The jump itself
arrived in Feb–Mar, rather than in the month of the changes.

**Figure 1.** Category A COE clearing price, 2016–2025, with the verified
policy changes marked.

![Category A COE clearing price over time, with the verified policy changes marked](charts/01_price_regime.png)

*Nominal prices. Dotted gray lines mark the verified rebate changes
(Jan 2018, Jan 2021, Jan 2024); the dashed red lines mark the two
non-rebate rule changes: the Jan 2022 tax (minimum registration tax for
EVs to zero) and the May 2022 engine-threshold change.*

What the categories say: **of the two categories where no EV rebate ever
applies (C: goods vehicles & buses; D: motorcycles), D moved like A — in
fact more (+13.1% vs +6.4%) — while C moved the other way (−11.4%)**
(Figure 2). That split means the test can't cleanly rule out a market-wide
shock, and it can't establish an EV-specific cause either (the "open"
category E, where EV cars may also bid, moved with the car categories at
+11.8% — as expected). The decisive facts are that the Jan 2022 change
was a *tax rule*, not a change to the rebate, and that the estimated 2022-01
effect is not statistically robust (p = 0.061).

**Figure 2.** The negative-control test for the 2022 jump: estimated 2022-01
% price jump by car category, each measured over the full 2016–2025 window.

![Negative-control check: 2022-01 % price jump by car category (full window)](charts/02_negative_control_2022.png)

*Verdict: MIXED. The two rebate-free categories split — D (motorcycles)
jumped more than A (+13.1% vs +6.4%), C (goods & buses) moved the other
way (−11.4%) — so the jump is neither a clean market-wide signal nor a
clean EV-specific one. Because the Jan 2022 change was a tax rule rather
than a change to the rebate, the move is not credited to the EV rebate. B
(high-power EVs) and E (open; EV cars can bid) moved with the car
categories, as expected.*

*The price rise was also reported in the media. [The Straits Times](https://www.straitstimes.com/singapore/transport/coe-premiums-at-all-time-highs-in-2022-buyers-could-get-slight-reprieve-in-later-half-of-2023)
noted on 29 Dec 2022 that COE premiums went on "a relentless upward march
for much of 2022", setting all-time highs in four of the five categories,
driven by tight supply and strong demand. The
[LTA's official bidding results](https://www.lta.gov.sg/content/dam/ltagov/who_we_are/statistics_and_publications/statistics/pdf/M11-COE_Results_2020_2022.pdf)
show the same climb for Category A: the second-auction quota premium rose
from S$57,898 in Jan 2022 to S$71,556 in Mar 2022 (our panel's monthly
average of both auctions: S$57,748 to S$70,028). Notably, the Straits
Times piece also speculated that the rebates and the new engine-power
threshold rule may have pushed up Category A prices — the very question
this study tests.*

### 4.2. In the EV era, prices did respond to the 2024 rebate cut

Because the rebate changed *again* in Jan 2024 (S$45k → S$40k), the
2022–2025 window can be estimated on its own — the rebate amount varies
within it, so the statistics have something to work with. In that window
(41 months, with the May 2022 threshold change controlled):

- For every extra S$1,000 of maximum rebate, the average Category A price
  was about **S$4,090 higher** — a statistically clear association
  (95% CI S$2,060 to S$6,120; p = 0.00008; p = 0.0000009 with
  autocorrelation-robust standard errors; inflation-adjusted:
  +S$4,141 per S$1,000, 95% CI S$2,104 to S$6,178, p = 0.00007).
  Stated in terms of the Jan 2024 cut itself: it is associated with a price
  change of −S$20,449 (95% CI −S$30,602 to −S$10,297; p = 0.00008).
- The rebate-free categories (C goods & buses, D motorcycles) did **not**
  show the same 2024 move (−7.9% and −7.4% vs −23.0% for A; Figure 3),
  so this is plausibly EV-relevant (B and E are contaminated — EVs can
  bid in them — and moved with A, at −36.8% and −36.1%).
- But the window has only 41 months and two rebate levels, so this is a
  **low-power association, not a measured causal effect**. It's evidence
  the price system responded to the rebate cut — not a number to quote
  as "how much rebates raise prices".

**Figure 3.** The negative-control test for the 2024 rebate cut: estimated
2024-01 % price jump by car category (the rebate cut shows up as a price
drop), each measured over the 2022–2025 window.

![Negative-control check: 2024-01 % price jump by car category (2022+ EV era; the 2024-01 rebate cut shows up as a price drop)](charts/03_negative_control_2024.png)

*Verdict: the pattern fits an EV-rebate effect. The 2024 cap cut dropped
prices sharply in the car categories where EV rebates apply (A −23.0%,
B −36.8%, and the open category E, where EV cars may also bid, −36.1%),
but only mildly in the two categories with no EV rebate at all (C −7.9%,
D −7.4%) — less than a third as much. This doesn't prove the rebate
caused the drop, but a market-wide cause would have hit the no-rebate
categories just as hard.*

### 4.3. Rebates did not drive more bidding demand

If the rebate story were true, more customers would want an EV, and the
bidding demand in Category A — the bids are placed mostly by car dealers
on their customers' behalf — would rise with rebate generosity. It
didn't: across the decade the link is statistically zero (−3.1 bids per
S$1,000 of rebate, not significant, p = 0.66), and in the EV era it
points the other way (−109.5 bids per S$1,000, p = 0.012) — higher rebate
levels coincided with *fewer* bids, which is most consistent with noise
and mixing in non-EV demand (Category A is still mostly non-EV cars).
Figure 4 shows the price-vs-bids relationship directly; the EV uptake
(Figure 5) is examined in section 4.4.

**Figure 4.** Category A COE price (left axis) vs number of bids received
(right axis), over the full 2016-01..2025-05 window.

![Category A COE price (left axis) vs number of bids received (right axis)](charts/04_price_demand_dual.png)

*Price and bidding demand over the full window. The two series move
almost independently: the correlation over the decade (levels) is
r = −0.47, and month-to-month the correlation of changes is
r = +0.05 (price vs proportional change in bids) or r = +0.11 (both in
raw levels) — near zero either way. The negative level correlation is
driven by the 2018–2020 price spike coinciding with low bid levels. The
shaded regions show the max EV rebate in force at each point: S$45k
(lighter, 2022-01..2023-12) and S$40k (darker, 2024-01 onward); the dashed
line marks the Jan 2024 cut.*

### 4.4. EV adoption more than tripled — and did not follow the rebate

Figure 5 is the only direct look at the first link of the hypothesized
chain (rebate → more EV demand → more bids → higher price):

- EV registrations grew from about **420/month** on average
  before the Jan 2024 cut to about **1,310/month** after it — EVs went
  from about 12–18% of new cars (2022) to 28–37% (2024) and 38–43%
  (2025).
- The cut itself (S$45k → S$40k maximum rebate, dashed line) did not dent
  the trend: registrations dipped in Jan 2024, then kept climbing. EV
  uptake was growing for reasons other than the rebate — falling EV
  prices, model supply, charging build-out — and the rebate was not
  driving it.

That is what breaks the chain: the demand side does not track the rebate
level, so the via-bidding path (Figure 7) shows no effect. Policy was
also set in response to this very uptake — rebate and demand move
together by construction, which is part of why the study cannot credit
the rebates with the prices. (Bound: the series starts 2022-07, runs 35
months, and is a lower bound on the true counts — only about one in four
months' rows carry counts — so this is descriptive evidence, not a
measured effect.)

**Figure 5.** EV registrations and their share of new-car sales,
with the data-coverage lower bound.

![EV registrations and their share of new cars, with the data-coverage lower bound](charts/05_ev_demand.png)

*EV registrations and their share of new-car registrations from
2022-07 (when the official EV label first appears); bars are a lower
bound because many months' rows have no count (mean coverage 23%). The
dashed line marks the Jan 2024 cut of the maximum rebate from S$45k to
S$40k; adoption kept rising after it.*

### 4.5. Prices and bidding demand barely track each other

A basic requirement for "more bidding → higher prices" is that price and
bids actually move together. Across the decade they don't — in fact the
decade-level relationship runs the wrong way (months with more bids had
*lower* prices, Figure 6), and month to month the two series barely
track each other.

**Figure 6.** Each dot is a month: Category A price vs bids received, with
the best-fit line and its uncertainty band.

![Each dot is a month: Category A price vs bids received, with the best-fit line and its uncertainty band](charts/06_scatter_fit_ci.png)

*Simple linear fit (association only, no controls): the slope is
negative — months with more bids had lower prices (about
−S$7.4k per additional 1,000 bids; 95% CI −S$9.5k to −S$5.2k;
p < 0.001; level correlation r = −0.47), the opposite of what the
"more bids → higher prices" mechanism predicts. Month to month the two
series barely track each other (correlation of raw changes r = +0.11;
price vs proportional change in bids r = +0.05): more bids did not
reliably translate into higher prices.*

### 4.6. The "rebate → more bids → higher price" chain is broken

If the rebate pushed prices up because more people wanted to bid on EVs,
two things should be visible: the rebate should move bidding demand, and
bidding demand should move the price. The previous sections already
looked at both:

- The rebate does not move bidding demand. Across the decade the
  association is zero (−3.1 bids per S$1,000, not significant,
  p = 0.66), and in 2022–25 it points the other way (−109.5 bids per
  S$1,000, p = 0.012) — higher rebate levels coincided with *fewer* bids
  (section 4.3, Figure 4); EV registrations tell the same story
  (section 4.4, Figure 5).
- Bidding does not move the price. Bids received one month earlier
  explain essentially none of the next month's clearing price
  (−S$0.02 per bid, not significant, p = 0.98) (section 4.5, Figure 6).

So neither link of the chain holds up, and the chain check agrees
(Figure 7): the share of the rebate's price effect routed through
bidding is zero within its uncertainty in both windows (full decade:
−0.4%, 95% CI −3.8% to +2.5%). Whatever small rebate–price connection the
study does find — the one in the EV era — is therefore not being carried
by more bidding.

**Figure 7.** The hypothesized chain — rebate → bidding demand → price —
with, for each link in the chain, what we should see if the hypothesis were true and
what we actually see.

![The hypothesized chain: rebate → bidding demand → price; for each link, the prediction if the hypothesis were true and the observed result](charts/07_mediation_diagram.png)

*The chain check from section 4.6: each arrow shows what we would
expect if the hypothesis were true and what the data show (p-values as
labeled); the box below shows the share of the rebate's price effect
routed via bidding, in each time window. Coefficients and confidence
intervals for every link: report §3.2 (bidding channel) and §3.4
(mediation).*

### 4.7. Looking at each policy change individually doesn't help either

An "event study" examines prices around each of the five verified policy
changes (the three changes to the rebate amount, plus the Jan 2022 tax
and the May 2022 threshold). Every single one shows the price was already drifting in that
direction *before* the policy started (Figure 8) — the signature of the
long-run COE price trend (plus the pandemic-era dip in 2020), not of the
policy itself. The estimated effects are therefore reported as bounds,
not point estimates.

The onset estimates themselves: Jan 2018 −S$17,068 (95% CI −S$19,592 to
−S$14,543, p < 0.001); Jan 2021 +S$11,145 (+S$8,142 to +S$14,148,
p < 0.001); Jan 2022 +S$26,922 (+S$18,997 to +S$34,846, p < 0.001);
May 2022 +S$27,947 (+S$14,376 to +S$41,518, p < 0.001) — the threshold
change is associated with a sustained post-onset price lift of about
S$39k–46k over the following year; Jan 2024 −S$39,017 (−S$43,178 to
−S$34,856, p < 0.001). All five pre-trends are statistically
contaminated (joint test of the pre-change months: p < 0.001 in every
episode), so none is a clean causal jump.

One might object that this drift is itself the market *anticipating* each
change — in which case it would be part of the policy effect. The
direction fits: prices were climbing in the six months before the 2021
and 2022 changes, falling before the 2024 cap cut, and only the 2018
change (a low-emission-era policy, not an EV rebate) drifted the other
way. But the shape of the drift argues against anticipation: an
anticipatory move shows up as a one-off jump near the announcement, while
the 2021 and 2022 drifts are smooth, steady ramps across all six months —
the same underlying price cycle that lifted every COE category, including
those with no EV rebate at all (section 4.1). The 2024 pre-trend is the
one exception: a gentle drift for four months, then a sharp drop in the
last two (the month before the cut sits about S$28k below where the
earlier drift would have put it), the shape most consistent with
anticipation of an already-announced cut. The five events also sit on
opposite slopes of one long price cycle, so a single underlying trend can
produce the same pattern; with this data the study cannot separate "the
market was anticipating the change" from "the market was already
drifting."

**Figure 8.** Estimated price changes around each of the five verified
policy changes, with uncertainty bars.

![Estimated price changes around each of the five policy changes, with uncertainty bars; the pre-change "leads" should be zero if the policy caused the move](charts/08_event_study.png)

*One panel per policy change (2018 VES onset, 2021 EEAI stack, 2022-01
tax floor, 2022-05 engine threshold, 2024 cap cut). The left side of each
panel (months *before* the change) already shows large non-zero moves —
the pre-trend problem. The right side shows aggregated bins (months 1–6,
7–12, 13 onward; the horizontal span marks the months covered, an arrow
means the bin runs beyond the displayed window).*

### 4.8. What we can and can't claim

- **Can claim:** no detectable EV-specific effect of the rebates on COE
  prices or bidding across the decade; the 2022 price jump showed up in
  a rebate-free category too (D motorcycles, more than in A), while the
  other rebate-free category (C) moved the other way — the test is mixed,
  and the 2022 change was a tax rule, not a change to the rebate; prices
  and bidding demand are weakly related; the via-bidding chain is broken; EV
  adoption more than tripled but did not track the rebate level — it kept
  rising after the Jan 2024 cut.
- **Can't claim:** a precise "rebates raise prices by X" number. The
  rebate policy was itself *set in response to* EV demand (policy and
  outcome move together by construction), the samples are small, and the
  one detected association sits in a 41-month window with two rebate
  levels.

## 5. Under the hood (for the curious)

**How the study works.** The design's core trick: the rebate amount
changed three times over 2016–2025 (plus two non-rebate rule changes that
are controlled separately), so months can be compared across rebate
levels. Everything is estimated on the full decade (110 months with
auctions), and the 2022–2025 "EV era" is estimated separately too,
because the rebate amount changes *within* that window (the 2024 cap
cut). A guard module checks this programmatically before any result is
produced (`src/05_scope_guard.py`).

**Reproducibility.** Every number in the report traces to a file: raw data
in `data/raw/` (with a provenance record tying each download to its
source), processed panels in `data/processed/`, one CSV per table in
`tables/`, eight charts in `charts/` (Figures 1–8), and the reports in
`docs/`. A verification module re-checks row counts, citations, and that
every quoted figure matches its source table (the current run passes all
9 checks; the per-figure trace is in
`tables/report_figures_checklist.csv`).

**Re-running it.**

```bash
python3 -m pip install pandas statsmodels matplotlib
cd <repo root>
python3 src/01_fetch.py         # optional: re-download the three data.gov.sg stores (fails on count mismatch)
python3 src/00_data.py          # data-layer checks + corrected bid counts
python3 src/02_coe_panel.py     # monthly COE panel (all five categories)
python3 src/03_registrations.py # monthly registration panel + EV share
python3 src/04_panel_rebate.py  # joins the verified rebate dose/dummies onto the panel
python3 src/05_scope_guard.py   # runs all exhibits (06-12) and audits the scope rules
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
charts/                    ← the eight charts shown above (Figures 1–8)
src/                       ← 16 ordered Python modules (fetch → panel → exhibits → verify → report) + shared bootstrap
```
