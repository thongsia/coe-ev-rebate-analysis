# Do EV rebates make COE bidders bid more?

An empirical analysis of whether Singapore's EV rebate system affects **COE
(Certificate of Entitlement) bidding prices and final clearing prices** —
specifically, whether the *offer* of a rebate causes bidders to bid more.
EV rebates are used as the case study.

> **Bottom line (honest):** The EV rebate offer does **not** detectably cause
> bidders to bid more, or raise Category A COE clearing prices, *through an
> EV-specific channel*. The only nominally significant price coefficient
> **fails the negative-control test** — categories to which no EV rebate
> applies at all show the same or larger price jump — pointing to a
> market-wide common shock rather than a rebate effect. Every causal link
> in the study grades **not detectable**; the evidence is associational at
> best, given endogeneity and low statistical power. See
> [`docs/REPORT.md`](docs/REPORT.md) for the full report.

---

## 1. Study objectives

1. **Primary question:** Does the offer of an EV rebate cause people to bid
   more in the COE auction (i.e. raise Category A bidding demand and the
   clearing price)?
2. **Mechanism under test (indirect channel):** EV rebates (VES/CEVS/EEAI,
   incl. the 45%-of-ARF rebate) lower the *total cost of owning an EV*, not
   the COE premium directly. The hypothesized path is:

   ```
   rebate → lower EV cost → more EV demand → higher Cat A COE demand → higher clearing price
   ```

   The analysis tests each link of this chain and decomposes the total effect
   into the indirect (mediated) path vs. a residual direct path.
3. **Counterfactual discipline:** Because rebates have been continuously in
   place (with gradual changes) rather than a clean on/off switch, the design
   must separate any rebate effect from confounders that move COE prices
   independently — most importantly the Jan 2022 Category A power-threshold
   change (97 → 110 kW), the 2026 PARF cuts, and the 2026 COE supply trough.

## 2. Study design

### 2.1 Data & panel

- **Joint analysis window: 2016-01 → 2025-05** (113 months; 110 with COE
  exercises — 2020-04/05/06 were suspended, documented and listwise-dropped).
  Registrations end 2025-05, so 2025-06 → 2026-10 is a **COE-only descriptive
  extension**, excluded from all joint models.
- COE exercises run **1–2 per month**, so a single documented collapsing rule
  is applied: *mean* clearing price across a month's exercises per category;
  *sum* of bids and quota; an `exercise_count` audit column whose per-category
  sums must reconcile exactly to raw row counts (they do: 220 per category in
  the window).

### 2.2 The estimable-scope rule (the design's critical decision)

Within the joint window there are exactly **4 rebate-level changes** (Nov 2016
up, Jan 2018 down, Sep 2018 up, Jan 2022 up), and the rebate level is **flat
from Jan 2022 to the window end**. Therefore:

- Every rebate-intensity exhibit (price equation, bidding channel, mediation)
  is **estimated on the full joint window** — the only scope where the rebate
  dose spans multiple levels.
- A **2022+-only estimation sample is rank-deficient** (dose and the Jan-2022
  dummy are each constant there), so no rebate coefficient is estimable on
  it. **2022+ is the *interpretation* scope only** (the EV-relevant era); it
  is reported as a bounded robustness check, never as the estimation sample.
- This rule is enforced *programmatically* by `src/05_scope_guard.py`
  (assertions logged to `tables/scope_audit.csv`, 8/8 PASS) and re-verified
  by `src/14_verify.py`.

### 2.3 Causal exhibits

| Exhibit | Specification | Estimation scope |
|---|---|---|
| **Price equation** | Cat A clearing price (nominal + real) on lagged (t-1, t-2) Cat A bids received, rebate regime dummies + continuous dose (separate specs), quota, time trend, CPI, confounder dummies; OLS with robust (HC1) and HAC (Newey-West) SEs | full window; 2022+ robustness bounded |
| **Bidding channel** | Cat A bids received on rebate intensity + trend + quota + confounders; cross-lag check (lag ±1) | full window |
| **Registration channel** | EV registrations + EV share + coverage rate (descriptive/correlational only — no within-window rebate variation) | 2022-07 → 2025-05 |
| **Mediation** | rebate → bids → price decomposed into indirect + direct paths; 2-stage bootstrap CIs (2000 resamples); mediated (indirect/total) share | full window |
| **Event study** | Coefficients + CIs around each regime change; 2016-2018 changes treated as **one episode**; Jan 2022 co-occurring threshold dummy controlled; windows span pre- and post-treatment (leads defined); pre-trends checked | per event |
| **Negative controls** | Price/demand re-estimated on Categories C, D, E (no EV rebate — clean controls) and B (contaminated upper bound) | full window |
| **Evidence grading** | Each link graded *supported / directionally consistent / not detectable*; low-power and endogeneity caveats restated; precise magnitude claims forbidden | per link |

### 2.4 Data-flow/layering contract

The pipeline is strictly ordered and re-runnable: each numbered module reads
only from `data/raw` or earlier `data/processed` files and writes only to
`data/processed` or the output directories. A single pinned provenance record
(`data/raw/provenance.csv`) ties every fetched row count to its stated source
total, so **every number in the report traces to a concrete upstream file**
(69/69 report figures verified — `tables/report_figures_checklist.csv`).

## 3. Datasets

All three stores are public on
[data.gov.sg](https://data.gov.sg), auth-free. Raw CSVs and pinned provenance
are in [`data/raw/`](data/raw/) (`provenance.csv` records resource id,
retrieval timestamp, stated total, and fetched count — all reconciled `OK`).

| Store | Resource ID | Rows | Coverage | Notes |
|---|---|---|---|---|
| COE bidding results | `d_69b3380ad7e51aff3a7dcc84eba52b8a` | 1,985 | 2010-01 → 2026-10 | one row per (month, category A–E, exercise); clearing premium, quota, bids received/successful. **Category E is the motorcycle category**, not an EV category. |
| Monthly new-car registrations | `d_d3f4d708e1d0a37b4365414e2fad3a07` | 51,669 | 2016-01 → 2025-05 | by make/fuel/vehicle type. The `Electric` (BEV) label first appears **2022-07**; `Petrol-Electric` hybrids kept separate. The count field is null on ~57% of rows (rising over time), so EV totals are **lower bounds** reported with a monthly coverage rate. |
| CPI All Items (2024 base) | `d_bdaff844e3ef89d39fceb962ff8f0791` | 207 | monthly | deflates the Cat A clearing price to real terms (an annual-inflation fallback was considered and rejected because monthly CPI is available). |

### Rebate regime timeline (with verified-policy caveats)

The 4 in-window regime changes encoded as step dummies + a continuous
"maximum total EV rebate available" dose are documented in
`tables/rebate_timeline.csv` with per-change policy citations. **Important
caveat:** the schedule's pre-2022 levels are nominal case-study constructs
(directions per the study design; magnitudes not independently verifiable).
Only the **$7,500** dose anchor is a verified policy figure. Verified LTA/NEA
policy differs in detail (real EEAI introduced 1 Jan 2021 at a $20k cap →
$15k (2024) → $7.5k (2026); VES from Jan 2018; CEVS ran through Dec 2017; the
actual Jan 2022 change was the $0 ARF floor). These discrepancies are
documented per change, cited, and flagged — the identification logic depends
on the flat 2022+ dose, which holds under both schedules.

## 4. Analysis

A 16-module Python pipeline (`src/`, pandas + statsmodels + matplotlib) runs
in strict order and is fully re-runnable:

```
01_fetch → 02_coe_panel → 03_registrations → 04_panel_rebate   (data + panel)
05_scope_guard                                                  (enforces scope rules)
06_price_equation → 07_demand_bidding → 08_demand_registration (causal exhibits)
09_mediation → 10_event_study → 11_diagnostics → 12_grading    (mechanism + robustness)
13_charts → 14_verify → 15_report                              (outputs)
```

Outputs: processed panels in `data/processed/`, one CSV per reported table in
`tables/` (27 tables incl. per-chart data tables), six charts in `charts/`,
and the two reports in `docs/`. `14_verify.py` re-runs 9 reconciliation checks
(row-count, audit-sum, source-citation, figure-traceability, scope) — the run
in this repo scored **PASS 9/9**.

### How to re-run

```bash
python3 -m pip install pandas statsmodels matplotlib
# from the repo root:
python3 src/01_fetch.py         # re-fetches all three stores (hard-fails on count mismatch)
python3 src/05_scope_guard.py   # runs modules 06–12 in order, then audits scope
python3 src/13_charts.py
python3 src/14_verify.py
python3 src/15_report.py
```

## 5. Key insights

1. **The headline price coefficient fails its negative control.** The full-window
   price equation shows a positive Jan-2022 coefficient (**+5,880 S$**, p=0.034
   HC1, 95% CI [444, 11,317]; dose +2,349 S$/1000 S$, p<0.001; no
   nominal↔real reversal). But rebate-free **Categories C/D/E show the same or
   larger** 2022-01 price jump (C +13.7%, D +41.8%, E +36.4% vs A's +10.1%).
   The 2022 increase is therefore best read as a **market-wide common shock**
   co-timed with the 97→110 kW threshold change — **not an EV-rebate-specific
   effect**.

2. **The rebate does not detectably raise bidding demand.** Cat A bids received
   show a **−278-bid** Jan-2022 coefficient that is *not robust* to HAC
   standard errors (HC1 p=0.040 → HAC p=0.120) and a null dose term. Total
   Category A demand is dominated by non-EV cars; its EV-signal is material
   only from ~2022. So the direct "bidders bid more" link is **not supported**.

3. **The indirect (mediated) path is null.** The rebate→bidding→price indirect
   effect is −43 (CI spans 0) and the mediated share is **−0.015** (CI spans 0):
   whatever price effect exists is **not routed through Category A bidding
   demand**. The EV-registration channel is descriptive only (no within-window
   rebate variation; EEAI is a constant baseline), so it cannot carry the
   mechanism either.

4. **All four causal links grade *not detectable*** (rebate→price headline,
   rebate→demand bidding, rebate→demand registration, demand→price, and the
   total indirect effect). Event-study pre-trends for both episodes are
   contaminated by the secular COE price trend, so event effects are reported
   as bounds. Prices and demand are I(1) with strong residual autocorrelation
   (DW ≈ 0.79), which is why HAC standard errors are used throughout.

5. **Honest framing.** With only 4 effective treatment changes and ~110 monthly
   observations, power is low and the rebate policy is endogenous (set in
   response to EV demand; registrations depend on the COE price paid). The
   study therefore **declines to claim a precise causal magnitude** — its
   defensible conclusion is the *absence* of detectable EV-specific evidence,
   not a quantified effect size.

## 6. Repository layout

```
├── README.md                  ← this file
├── docs/
│   ├── REPORT.md              ← full written report (exec summary, data, results, limitations)
│   └── STATS_SUMMARY.md       ← one-page statistical summary
├── data/
│   ├── raw/                   ← verbatim source CSVs + provenance.csv
│   └── processed/             ← coe_monthly, ev_registrations, cpi_deflated, panel_joint, COE extension
├── tables/                    ← one CSV per reported table (incl. per-chart data tables)
├── charts/                    ← 01–06 PNGs (price+regime w/ negative-control panel, EV demand,
│                                │   price-vs-demand dual, scatter+CI, event study, mediation diagram)
├── src/                       ← 17 re-runnable pipeline modules (00_data … 15_report)
└── .gitignore
```

**Charts:**
- [`charts/01_price_regime.png`](charts/01_price_regime.png) — nominal + real Cat A price with regime/confounder markers **and the negative-control comparison**
- [`charts/02_ev_demand.png`](charts/02_ev_demand.png) — EV registrations + share with coverage lower-bound
- [`charts/03_price_demand_dual.png`](charts/03_price_demand_dual.png) — dual-axis price vs bids
- [`charts/04_scatter_fit_ci.png`](charts/04_scatter_fit_ci.png) — price-vs-demand scatter with fit + CI band
- [`charts/05_event_study.png`](charts/05_event_study.png) — event-study coefficients with CIs
- [`charts/06_mediation_diagram.png`](charts/06_mediation_diagram.png) — mediation path with effect sizes

---

*Analysis window 2016-01 → 2025-05 (joint) + 2025-06 → 2026-10 (COE-only
extension). Generated by the KAKIS research→plan→synthesize→execute pipeline
(Igor feasibility → Dory iterative planning, 6 iterations → Bob best-of-breed
synthesis → 3 sequential execution batches). All figures trace to `tables/*.csv`.*
