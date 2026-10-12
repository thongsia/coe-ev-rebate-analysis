# STATS SUMMARY — one page

**Question:** does the EV-rebate offer cause COE bidders to bid more?  
**Answer (honest):** not detectable as an EV-rebate-specific effect. The 2022-01 price jump is a market-wide common shock (negative-control FAIL); all causal links grade *not detectable*; evidence is associational at best (endogeneity + low power).

**Scopes.** Estimation scope = **full window 2016-01..2025-05** (listwise N=110; 3 pandemic months dropped; nobs≈108) for every rebate-intensity exhibit — the dose is flat 7500 from 2022-01, so a 2022+-only estimation is rank-deficient (NA by design). Interpretation scope = **2022-01..2025-05** (EV-relevant era); 2022+ numbers elsewhere are interpretation/robustness only.

| Quantity | Value | Source |
|---|---|---|
| Headline reg_eeai_202201 (nominal, M1, HC1) | **+5,880 S$** [444, 11,317], p=0.034 (HAC p=0.104) | price_equation.csv |
| Headline real | +7,532 S$ [CI95 1,644, 13,421], p=0.0122 — no nominal↔real reversal | price_equation.csv |
| Dose/1000 S$ (nominal / real, M3, HC1) | +2,349 [1,577, 3,121], p=2.45e-09 / +2,824, p=2.66e-10 | price_equation.csv |
| rebate→bidding (dummy / dose, HC1) | -278 bids (p=0.04; **HAC p=0.12 → not robust**) / -25.1 bids (p=0.422 → null) | demand_bidding_channel.csv |
| demand→price (lag-1, nominal, M1, HC1) | -1.039 S$/bid [-2.719, +0.640], p=0.225 → n.s. | price_equation.csv |
| mediation (indirect / total / mediated share) | -43.4 [/ +2897.4] → share -0.015 (CI spans 0) → **NOT routed through bidding** | mediation_effects.csv |
| event-study 2022-01 onset (bounded; pre-trend contaminated) | +22,683 S$ [13,995, 31,370], p=3.1e-07 | event_study_coefficients.csv |
| **negative-control 2022-01 % jumps** | A +10.1% (EV-eligible) vs **C +13.7% / D +41.8% / E +36.4% (no EV rebate)** → **FAIL → market-wide common shock** | negative_controls.csv |
| diagnostics | prices/demand I(1); DW 0.7910; LB Q(1) p=1.14e-09 → HAC SEs; 4 events / 110 obs (low power) | diagnostics_stationarity_autocorr.csv |

**Grades (`evidence_grading.csv`):** rebate→price (headline) = **not detectable** (negative-control FAIL); rebate→demand (bidding) = not detectable; rebate→demand (registration) = not detectable (descriptive only); demand→price = not detectable; mediation = not detectable.

*All values copied from `tables/*.csv`; see REPORT.md for the full derivation and `tables/verification_report.csv` for the verification pass.*